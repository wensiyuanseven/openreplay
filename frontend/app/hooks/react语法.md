在分析所有文件后，这些自定义 React Hook 中使用了一些关键的 React 语法和概念。以下是文件中用到的主要 React 语法和每个语法的用法场景和示例：

### React 语法和用法场景

1. **`useState`**
   - **用法**: `useState` 是 React 提供的一个 Hook，用于在函数组件中添加状态管理。
   - **场景**: 适用于需要管理局部状态的场景，如表单输入、布尔开关、计数器等。
   - **语法**:
     ```jsx
     const [state, setState] = useState(initialState);
     ```
   - **示例**:
     ```jsx
     import React, { useState } from 'react';

     function Counter() {
       const [count, setCount] = useState(0);

       return (
         <div>
           <p>You clicked {count} times</p>
           <button onClick={() => setCount(count + 1)}>Click me</button>
         </div>
       );
     }
     ```

2. **`useEffect`**
   - **用法**: `useEffect` 是一个 Hook，用于在组件渲染后执行副作用操作，如数据获取、订阅、手动 DOM 操作等。
   - **场景**: 适用于需要在组件生命周期的特定阶段（如挂载、更新、卸载）执行操作的场景。
   - **语法**:
     ```jsx
     useEffect(() => {
       // effect
       return () => {
         // cleanup
       };
     }, [dependencies]);
     ```
   - **示例**:
     ```jsx
     import React, { useState, useEffect } from 'react';

     function Example() {
       const [count, setCount] = useState(0);

       useEffect(() => {
         document.title = `You clicked ${count} times`;
       }, [count]); // 仅在 count 更改时重新运行

       return <button onClick={() => setCount(count + 1)}>Click me</button>;
     }
     ```

3. **`useCallback`**
   - **用法**: `useCallback` 返回一个记忆化的回调函数，它仅在其依赖项更改时更新。常用于优化性能，避免在子组件不必要的重新渲染。
   - **场景**: 适用于需要在依赖项不变的情况下避免重新生成函数的场景，特别是在将回调函数传递给子组件时。
   - **语法**:
     ```jsx
     const memoizedCallback = useCallback(
       () => {
         doSomething(a, b);
       },
       [a, b],
     );
     ```
   - **示例**:
     ```jsx
     import React, { useState, useCallback } from 'react';

     function Parent() {
       const [count, setCount] = useState(0);
       const handleClick = useCallback(() => {
         setCount(c => c + 1);
       }, []); // `handleClick` 仅在组件挂载时创建一次

       return <Child onClick={handleClick} />;
     }

     function Child({ onClick }) {
       return <button onClick={onClick}>Click me</button>;
     }
     ```

4. **`useRef`**
   - **用法**: `useRef` 返回一个可变的 ref 对象，该对象的 `.current` 属性持有该 ref 的值。`useRef` 通常用于存储对 DOM 元素的引用或保存不需要引起重新渲染的变量。
   - **场景**: 适用于需要直接访问 DOM 元素或在渲染周期之间保持不变的值的场景。
   - **语法**:
     ```jsx
     const refContainer = useRef(initialValue);
     ```
   - **示例**:
     ```jsx
     import React, { useRef, useEffect } from 'react';

     function TextInputWithFocusButton() {
       const inputEl = useRef(null);

       const onButtonClick = () => {
         inputEl.current.focus();
       };

       return (
         <>
           <input ref={inputEl} type="text" />
           <button onClick={onButtonClick}>Focus the input</button>
         </>
       );
     }
     ```

5. **`useMemo`**
   - **用法**: `useMemo` 返回一个记忆化的值，只有在依赖项更改时才会重新计算。它常用于优化性能，避免在渲染时重复计算高成本的操作。
   - **场景**: 适用于需要优化性能、避免不必要计算的场景，特别是在复杂计算或大数据处理时。
   - **语法**:
     ```jsx
     const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);
     ```
   - **示例**:
     ```jsx
     import React, { useMemo } from 'react';

     function ExpensiveComponent({ a, b }) {
       const computedValue = useMemo(() => {
         return expensiveCalculation(a, b);
       }, [a, b]); // 仅在 a 或 b 改变时重新计算

       return <div>{computedValue}</div>;
     }
     ```

6. **`React.ChangeEventHandler` 和 `HTMLInputElement` 类型**
   - **用法**: 在 TypeScript 中，`React.ChangeEventHandler` 是一个泛型类型，用于定义输入元素的 `onChange` 事件处理程序。
   - **场景**: 适用于需要处理输入元素的事件处理程序的场景，特别是在 TypeScript 项目中定义强类型的事件处理函数时。
   - **语法**:
     ```tsx
     const handleChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
       console.log(event.target.value);
     };
     ```
   - **示例**:
     ```tsx
     import React, { useState, ChangeEvent } from 'react';

     function TextInput() {
       const [value, setValue] = useState<string>('');

       const handleChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
         setValue(event.target.value);
       };

       return <input type="text" value={value} onChange={handleChange} />;
     }
     ```

### 总结

这些 React 语法和 Hook 提供了开发现代 React 应用程序的基础工具。通过使用这些工具，开发者可以在函数组件中管理状态、副作用、优化性能和处理事件。上述每个语法都有其特定的使用场景和适用性，帮助开发者创建高效、可维护和响应式的应用程序。如果你有其他问题或者需要更多关于 React 的信息，请告诉我！