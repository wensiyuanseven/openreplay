import React from 'react';
import { Button, Space, Progress } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';

interface CardProps {
  title: string;
  extra?: React.ReactNode;
  children: React.ReactNode;
}

function Card(props: CardProps) {
  return (
    <div className='border p-3 rounded bg-white'>
      <div className='flex justify-between items-center'>
        <div className='font-medium'>{props.title}</div>
        <div>{props.extra}</div>
      </div>
      <div className='mt-2'>{props.children}</div>
    </div>
  );
}

function Statistics() {
  return (
    <div className='flex flex-col gap-4'>
      <div className='grid grid-cols-4 gap-4'>
        <Card title='Upcoming Maintenance' extra={
          <Button type='link'>Edit</Button>
        }>
          Monday, June 15, 2020 10:00 AM
        </Card>

        <Card title='Last Backup' extra={
          <Button type='link'>Edit</Button>
        }>
          Today at 10:00 AM
        </Card>


        <Card title='Data Retention' extra={
          <Button type='link'>Edit</Button>
        }>
          90 Days
        </Card>

        <Card title='Single-Sign-On (SSO)' extra={
          <Button type='link'>Edit</Button>
        }>
          <Space>
            <CheckCircleOutlined />
            Okta SAML 2.0
          </Space>
        </Card>
      </div>

      <div className='grid grid-cols-3 gap-4'>
        <Card title='CPU Usage'>
          <Progress percent={30} />
        </Card>

        <Card title='Memory Usage'>
          <Progress percent={50} />
        </Card>


        <Card title='Disk Usage' extra={
          <Button type='link'>Manage Space</Button>
        }>
          <Progress percent={94} strokeColor='red' />
        </Card>
      </div>
    </div>
  );
}

export default Statistics;