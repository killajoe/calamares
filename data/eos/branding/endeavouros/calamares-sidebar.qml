/* Sample of QML progress tree.

   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
   SPDX-FileCopyrightText: 2021 - 2022 Anke Boersma <demm@kaosx.us>
   SPDX-License-Identifier: GPL-3.0-or-later


   The progress tree (actually a list) is "horizontal" in this example,
   with the steps going to the right.
*/
import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.3
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: sideBar;
    color: Branding.styleString( Branding.SidebarBackground );
    height: 45;
    width: parent.width

    RowLayout {
        anchors.fill: parent;
        spacing: -10;


        Item {
            Layout.fillHeight: true;
        }

        Repeater {
            model: ViewManager
            Rectangle {
                Layout.leftMargin: 2;
                Layout.fillWidth: true;
                Layout.alignment: Qt.AlignTop;
                height: 45;
                radius: 0;
                color: Branding.styleString( index == ViewManager.currentStepIndex ? Branding.SidebarBackgroundCurrent : Branding.SidebarBackground )

                Text {
                    anchors.verticalCenter: parent.verticalCenter;
                    anchors.horizontalCenter: parent.horizontalCenter
                    x: parent.x + 12;
                    color: Branding.styleString( index == ViewManager.currentStepIndex ? Branding.SidebarTextCurrent : Branding.SidebarText );
                    text: qsTr(display);
                    font.pointSize : index == ViewManager.currentStepIndex ? 10 : 9;
                }

                Rectangle {
                    height: 2
                    width: 800
                    anchors.bottom: parent.bottom;
                    border.color: Branding.styleString(ViewManager.currentStepIndex === index ?
                    Branding.SidebarTextCurrent : (ViewManager.currentStepIndex >= index ? Branding.SidebarTextCurrent : Branding.SidebarBackgroundCurrent))
                    border.width: 2

                    Image {
                        source: "pan-up-symbolic.svg"
                        id: image
                        anchors.verticalCenter: parent.verticalCenter;
                        anchors.verticalCenterOffset : -6
                        x: parent.x + 45;
                        fillMode: Image.PreserveAspectFit
                        height: 40
                        visible: index == ViewManager.currentStepIndex ? true : false
                    }
                }
            }
        }
    }
}
