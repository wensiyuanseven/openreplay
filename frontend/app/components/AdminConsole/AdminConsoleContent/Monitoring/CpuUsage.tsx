import React, { PureComponent } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Card } from 'antd';
import { Styles } from 'Components/Dashboard/Widgets/common';

const generateRandomData = (pages: any) => {
  const data = [];

  // Base values
  const baseUV = 2500;
  const basePV = 2500;
  const baseAmt = 1500;

  // Noise range (± value)
  const uvNoise = 1500;
  const pvNoise = 1500;
  const amtNoise = 1000;

  for (let i = 0; i < pages.length; i++) {
    data.push({
      name: pages[i],
      uv: baseUV + (Math.random() * uvNoise * 2 - uvNoise),  // Random number within range
      pv: basePV + (Math.random() * pvNoise * 2 - pvNoise),
      amt: baseAmt + (Math.random() * amtNoise * 2 - amtNoise)
    });
  }
  return data;
};

const pages = ['Page A', 'Page B', 'Page C', 'Page D', 'Page E', 'Page F'];


export default class CpuUsage extends PureComponent {
  static demoUrl = 'https://codesandbox.io/s/simple-area-chart-4ujxw';


  render() {
    const data = generateRandomData(pages);
    return (
      <Card bodyStyle={{ padding: '10px' }}>
        <ResponsiveContainer width='100%' height={200}>
          <AreaChart
            width={500}
            height={400}
            data={data}
            margin={{
              top: 10,
              right: 30,
              left: 0,
              bottom: 0
            }}
          >
            <CartesianGrid strokeDasharray='3 3' />
            <XAxis {...Styles.xaxis} dataKey='name' />
            <YAxis {...Styles.yaxis} />
            <Tooltip />
            <Area type='monotone' dataKey='uv' stroke='#8884d8' fill='#8884d8' />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    );
  }
}
