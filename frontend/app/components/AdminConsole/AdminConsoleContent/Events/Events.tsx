import React from 'react';

import { Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CloudUploadOutlined } from '@ant-design/icons';


interface DataType {
  key: string;
  name: string;
  time: string;
  by: string;
}


const columns: ColumnsType<DataType> = [
  {
    title: 'Event',
    dataIndex: 'name',
    key: 'name',
    render: (_, record) => (
      <Space size='middle'>
        <CloudUploadOutlined />
        <a>Invite {record.name}</a>
      </Space>
    )
  },
  {
    title: 'Time',
    dataIndex: 'time',
    key: 'time',
    width: 250,
  },

  {
    title: 'By',
    dataIndex: 'by',
    key: 'by',
    width: 250,
  }
];

const data: DataType[] = [
  {
    key: '1',
    name: 'Upgraded to 1.15.0',
    time: '04:00 PM, Jan 1, 2021',
    by: 'User',
  },
  {
    key: '2',
    name: 'Upgraded to 1.14.0',
    time: '04:00 PM, Jan 1, 2021',
    by: 'User',
  },
  {
    key: '3',
    name: 'Upgraded to 1.13.0',
    time: '04:00 PM, Jan 1, 2021',
    by: 'User',
  }
];

function Events(props) {
  return (
    <Table columns={columns} dataSource={data} size="small" />
  );
}

export default Events;