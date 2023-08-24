import React from 'react';
import CpuUsage from 'Components/AdminConsole/AdminConsoleContent/Monitoring/CpuUsage';

function Monitoring() {
  return (
    <div className='grid grid-cols-2 gap-4'>
      <CpuUsage />
      <CpuUsage />
      <CpuUsage />
      <CpuUsage />
    </div>
  );
}

export default Monitoring;