#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2014 Aurélien Gâteau <agateau@kde.org>
#   SPDX-FileCopyrightText: 2017 Alf Gaida <agaida@siduction.org>
#   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
#   SPDX-FileCopyrightText: 2019 Kevin Kofler <kevin.kofler@chello.at>
#   SPDX-FileCopyrightText: 2019-2020 Collabora Ltd
#   SPDX-License-Identifier: GPL-3.0-or-later
#
#   Calamares is Free Software: see the License-Identifier above.
#

import tempfile
import subprocess
import os

import libcalamares

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext


def pretty_name():
    return _("Mounting partitions.")

def mount_partition(root_mount_point, partition, partitions):
    """
    Do a single mount of @p partition inside @p root_mount_point.
    """
    # Create mount point with `+` rather than `os.path.join()` because
    # `partition["mountPoint"]` starts with a '/'.
    global_storage = libcalamares.globalstorage
    raw_mount_point = partition["mountPoint"]
    if not raw_mount_point:
        return

    mount_point = root_mount_point + raw_mount_point

    # Ensure that the created directory has the correct SELinux context on
    # SELinux-enabled systems.
    os.makedirs(mount_point, exist_ok=True)
    try:
        subprocess.call(['chcon', '--reference=' + raw_mount_point, mount_point])
    except FileNotFoundError as e:
        libcalamares.utils.warning(str(e))
    except OSError:
        libcalamares.utils.error("Cannot run 'chcon' normally.")
        raise

    fstype = partition.get("fs", "").lower()
    if fstype == "unformatted":
        return

    if fstype == "fat16" or fstype == "fat32":
        fstype = "vfat"

    device = partition["device"]

    if "luksMapperName" in partition:
        device = os.path.join("/dev/mapper", partition["luksMapperName"])

    if libcalamares.utils.mount(device,
                                mount_point,
                                fstype,
                                partition.get("options", "")) != 0:
        libcalamares.utils.warning("Cannot mount {}".format(device))

    # Special handling for btrfs subvolumes. Create the subvolumes listed in mount.conf
    if fstype == "btrfs" and partition["mountPoint"] == '/':
        # Root has been mounted to btrfs volume -> create subvolumes from configuration
        btrfs_subvolumes = libcalamares.job.configuration.get("btrfsSubvolumes", None)
        # Warn if there's no configuration at all, and empty configurations are
        # replaced by a simple root-only layout.
        if btrfs_subvolumes is None:
            libcalamares.utils.warning("No configuration for btrfsSubvolumes")
        if not btrfs_subvolumes:
            btrfs_subvolumes = [ dict(mountPoint="/", subvolume="/@") ]

        subvolume_mountpoints = [d['mountPoint'] for d in btrfs_subvolumes]
        # Check if listed mountpoints besides / are already present and don't create subvolume for those
        for p in partitions:
            if "mountPoint" not in p or not p["mountPoint"]:
                continue
            if p["mountPoint"] in subvolume_mountpoints and p["mountPoint"] != '/':
                btrfs_subvolumes = [d for d in btrfs_subvolumes if d['mountPoint'] != p["mountPoint"]]
        # Check if we need a subvolume for swap file
        swap_choice = global_storage.value( "partitionChoices" )
        if swap_choice:
            swap_choice = swap_choice.get( "swap", None )
            if swap_choice and swap_choice == "file":
                btrfs_subvolumes.append({'mountPoint': '/swap', 'subvolume': '/@swap'})
        # Store created list in global storage so it can be used in the fstab module
        libcalamares.globalstorage.insert("btrfsSubvolumes", btrfs_subvolumes)
        # Create the subvolumes that are in the completed list
        for s in btrfs_subvolumes:
            subprocess.check_call(['btrfs', 'subvolume', 'create',
                               root_mount_point + s['subvolume']])

        subprocess.check_call(["umount", "-v", root_mount_point])

        device = partition["device"]

        if "luksMapperName" in partition:
            device = os.path.join("/dev/mapper", partition["luksMapperName"])

        # Mount the subvolumes
        for s in btrfs_subvolumes:
            mount_option = "subvol={}".format(s['subvolume'])
            subvolume_mountpoint = mount_point[:-1] + s['mountPoint']
            if libcalamares.utils.mount(device,
                                    subvolume_mountpoint,
                                    fstype,
                                    ",".join([mount_option, partition.get("options", "")])) != 0:
                libcalamares.utils.warning("Cannot mount {}".format(device))


def run():
    """
    Mount all the partitions from GlobalStorage and from the job configuration.
    Partitions are mounted in-lexical-order of their mountPoint.
    """
    partitions = libcalamares.globalstorage.value("partitions")

    if not partitions:
        libcalamares.utils.warning("partitions is empty, {!s}".format(partitions))
        return (_("Configuration Error"),
                _("No partitions are defined for <pre>{!s}</pre> to use." ).format("mount"))

    root_mount_point = tempfile.mkdtemp(prefix="calamares-root-")

    # Guard against missing keys (generally a sign that the config file is bad)
    extra_mounts = libcalamares.job.configuration.get("extraMounts") or []
    extra_mounts_efi = libcalamares.job.configuration.get("extraMountsEfi") or []
    if not extra_mounts and not extra_mounts_efi:
        libcalamares.utils.warning("No extra mounts defined. Does mount.conf exist?")

    if libcalamares.globalstorage.value("firmwareType") == "efi":
        extra_mounts.extend(extra_mounts_efi)

    # Add extra mounts to the partitions list and sort by mount points.
    # This way, we ensure / is mounted before the rest, and every mount point
    # is created on the right partition (e.g. if a partition is to be mounted
    # under /tmp, we make sure /tmp is mounted before the partition)
    mountable_partitions = [ p for p in partitions + extra_mounts if "mountPoint" in p and p["mountPoint"] ]
    mountable_partitions.sort(key=lambda x: x["mountPoint"])
    for partition in mountable_partitions:
        mount_partition(root_mount_point, partition, partitions)

    libcalamares.globalstorage.insert("rootMountPoint", root_mount_point)

    # Remember the extra mounts for the unpackfs module
    libcalamares.globalstorage.insert("extraMounts", extra_mounts)
