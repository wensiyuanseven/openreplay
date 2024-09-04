import React, { useState } from 'react';
import { AutoComplete, Input } from 'antd';
import type { SelectProps } from 'antd/es/select';
import { observer } from 'mobx-react-lite';
import { useStore } from 'App/mstore';

const UserSearch = ({ onUserSelect }: { onUserSelect: (id: any) => void }) => {
  const [selectedValue, setSelectedValue] = useState<string | undefined>(undefined);
  const { userStore } = useStore();
  const allUsers = userStore.list.map((user) => ({
    value: user.userId,
    label: user.name,
  }));
  // 第一个 <> 是用来告诉 TypeScript，useState 中管理的状态的类型是 SelectProps<object>['options']。
  // SelectProps<object>['options'] 是一个类型访问表达式，它表示获取 SelectProps<object> 类型中 options 属性的类型。
  //   SelectProps<object>：这里的 SelectProps 是一个泛型接口或类型，接受一个类型参数。在这个例子中，传入的类型参数是 object。
  // ['options']：这个部分表示从 SelectProps<object> 类型中访问 options 属性的类型。
  // 结合在一起：useState<SelectProps<object>['options']>：这表示 useState 钩子的状态类型将是 SelectProps<object> 类型中的 options 属性的类型。
  // ([])：这部分是 useState 的初始值。在这个例子中，初始值是一个空数组 []
  const [options, setOptions] = useState<SelectProps<object>['options']>([]);

  React.useEffect(() => {
    if (userStore.list.length === 0) {
      userStore.fetchUsers().then((r) => {
        setOptions(
          r.map((user: any) => ({
            value: user.userId,
            label: user.name,
          }))
        );
      });
    }
  }, []);

  const handleSearch = (value: string) => {
    setOptions(
      value ? allUsers.filter((u) => u.label.toLowerCase().includes(value.toLocaleLowerCase())) : []
    );
  };

  const onSelect = (value?: string) => {
    onUserSelect(value)
    setSelectedValue(allUsers.find((u) => u.value === value)?.label || '');
  };

  return (
    <AutoComplete
      popupMatchSelectWidth={200}
      style={{ width: 200 }}
      options={options}
      onSelect={onSelect}
      onSearch={handleSearch}
      value={selectedValue}
      onChange={(e) => {
        setSelectedValue(e)
        if (!e) onUserSelect(undefined)
      }}
      onClear={() => onSelect(undefined)}
      onDeselect={() => onSelect(undefined)}
      size="small"
    >
      <Input.Search
        allowClear
        placeholder="Filter by team member name"
        size={'small'}
        classNames={{ input: '!border-0 focus:!border-0' }}
        style={{ width: 200 }}
      />
    </AutoComplete>
  );
};

export default observer(UserSearch);
