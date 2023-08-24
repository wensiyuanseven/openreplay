import React from 'react';
import { Card, Dropdown, Space, Tabs, Tag } from 'antd';
import { CloudUploadOutlined, CodeSandboxOutlined, DownOutlined } from '@ant-design/icons';
import Statistics from 'Components/AdminConsole/components/Statistics';
import AdminConsoleContent from 'Components/AdminConsole/AdminConsoleContent';


const { TabPane } = Tabs;

function AdminConsoleView() {

  return (
    <div className='flex flex-col gap-4'>
      <Card title='Admin Console' extra={
        <Space>
          <Tag className='bg-gray-lightest border-none'>
            <Space>
              <CodeSandboxOutlined />
              Version 1.15.0
            </Space>
          </Tag>

          <Tag className='bg-active-blue border-active-blue color-teal border-none'>
            <Space>
              <CloudUploadOutlined />
              Upgrade available
            </Space>
          </Tag>
        </Space>
      }>
        <Statistics />
      </Card>

      <AdminConsoleContent />
    </div>
  );
}

export default AdminConsoleView;