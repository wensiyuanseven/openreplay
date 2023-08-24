import React, { useState } from 'react';
import { Tabs } from 'antd';
import type { TabsProps } from 'antd';
import { toast } from 'react-toastify';
import onChange = toast.onChange;

const { TabPane } = Tabs;

export enum TabKey {
  Monitoring = '1',
  MaintenanceAndBackups = '2',
  SingleSignOn = '3',
  Events = '4'
}

const items: TabsProps['items'] = [
  {
    key: TabKey.Monitoring,
    label: 'Monitoring'
  },
  {
    key: TabKey.MaintenanceAndBackups,
    label: 'Maintenance & Backups'
  },
  {
    key: TabKey.SingleSignOn,
    label: 'Single Sign-On (SSO)'
  },
  {
    key: TabKey.Events,
    label: 'Events'
  }
];

interface Props {
  activeTab: string;
  onChange: (key: string) => void;
}

function AdminConsoleTabs(props: Props) {
  const { activeTab, onChange } = props;

  return (
    <Tabs
      defaultActiveKey='1'
      activeKey={activeTab}
      onChange={onChange}
    >
      {items?.map((item) => (
        <TabPane tab={item.label} key={item.key}></TabPane>
      ))}
    </Tabs>
  );
}

export default AdminConsoleTabs;