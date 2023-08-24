import React, { useState } from 'react';
import AdminConsoleTabs, { TabKey } from 'Components/AdminConsole/components/AdminConsoleTabs';
import { Card, Space } from 'antd';
import Monitoring from 'Components/AdminConsole/AdminConsoleContent/Monitoring';
import Maintenance from 'Components/AdminConsole/AdminConsoleContent/Maintenance';
import SSO from 'Components/AdminConsole/AdminConsoleContent/SSO';
import Events from 'Components/AdminConsole/AdminConsoleContent/Events';

function AdminConsoleContent() {
  const [activeTab, setActiveTab] = useState<string>(TabKey.Events);
  return (
    <Card
      title={
        <AdminConsoleTabs
          activeTab={activeTab}
          onChange={(key: string) => {
            setActiveTab(key);
          }}
        />
      }
      extra={
        <Space>
          Past

          {/*<Dropdown menu={{  }}>*/}
          {/*  <a onClick={(e) => e.preventDefault()}>*/}
          {/*    <Space>*/}
          {/*      Hover me*/}
          {/*      <DownOutlined />*/}
          {/*    </Space>*/}
          {/*  </a>*/}
          {/*</Dropdown>*/}
        </Space>
      }>
      {activeTab === TabKey.Monitoring && (<Monitoring />)}
      {activeTab === TabKey.MaintenanceAndBackups && <Maintenance />}
      {activeTab === TabKey.SingleSignOn && <SSO />}
      {activeTab === TabKey.Events && <Events />}

    </Card>
  );
}

export default AdminConsoleContent;