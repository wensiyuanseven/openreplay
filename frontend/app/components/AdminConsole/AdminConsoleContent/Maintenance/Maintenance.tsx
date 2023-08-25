import React from 'react';
import { Space, Tag, Typography } from 'antd';
import { CloudUploadOutlined, CodeSandboxOutlined } from '@ant-design/icons';

const { Text } = Typography;

function Maintenance() {
  return (
    <div>
      <div>
        <Space>
          <CloudUploadOutlined />
          <Text>Version</Text>
        </Space>


      </div>
    </div>
  );
}

export default Maintenance;