React.FC FC 是 Function Component 的缩写。
在 React 中，FC 表示函数组件（Function Component），这是 React 中一种用于定义组件的方式。

实现方式
```js
type ReactNode = ReactChild | ReactFragment | ReactPortal | boolean | null | undefined;

interface ReactElement<P = any, T extends string | JSXElementConstructor<any> = string | JSXElementConstructor<any>> {
  type: T;
  props: P;
  key: Key | null;
}

type ReactChild = ReactElement | string | number;
type ReactFragment = {} | ReactChild[];
type ReactPortal = any;  // Simplified for explanation

interface FunctionComponent<P = {}> {
  (props: P, context?: any): ReactElement<any, any> | null;
  propTypes?: WeakValidationMap<P>;
  contextTypes?: ValidationMap<any>;
  defaultProps?: Partial<P>;
  displayName?: string;
}

type FC<P = {}> = FunctionComponent<P>;

```

children是什么？


一个简化的实现示例
```js
type MyFC<P = {}> = (props: P & { children?: React.ReactNode }) => React.ReactElement | null;

interface MyComponentProps {
  title: string;
}

const MyComponent: MyFC<MyComponentProps> = ({ title, children }) => {
  return (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  );
};

```


源码中的备注


一些概念


