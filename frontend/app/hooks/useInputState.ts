
import React, { useState, useCallback } from 'react';
// type SupportedElements = HTMLInputElement | HTMLSelectElement; 是 TypeScript 中的类型别名和联合类型语法。
// 它允许你定义一个新的类型名称，这个类型可以是多种类型之一。通过这种方式，你可以提高代码的可读性和类型安全性，特别是在处理多种类型的场景时。
type SupportedElements = HTMLInputElement | HTMLSelectElement;

// 参数类型注解：state: string = "" 指定 state 为 string 类型，默认值是空字符串。
// 返回类型注解：[string, React.ChangeEventHandler<SupportedElements>, (value: string) => void] 表示函数返回一个元组：
// 第一个元素是一个字符串类型的状态值。
// 第二个元素是一个事件处理函数（React.ChangeEventHandler<SupportedElements>），适用于 HTMLInputElement 或 HTMLSelectElement。
// 第三个元素是一个函数 (value: string) => void，用于直接设置状态值。

export default function (state: string = ""): [string, React.ChangeEventHandler<SupportedElements>, (value: string) => void] {
	// 泛型类型注解：useState<string> 指定状态的类型为 string，确保状态和更新函数的类型安全。
	const [value, setValue] = useState<string>(state);
	// useCallback 用于创建一个记忆化的回调函数。
	// const onChange = useCallback(
	// 	(event) => {
	// 		const { value } = event.target; // 解构赋值
	// 		setValue(value);
	// 	},
	// 	[] // 依赖项数组为空，表示只在挂载时创建一次
	// );
	// const person = {
	// 	name: 'Alice',
	// 	age: 25,
	// 	address: {
	// 	  city: 'New York',
	// 	  zip: '10001'
	// 	}
	//   };
	//  // 嵌套解构：从 person 对象的 address 属性中提取 city
	//   const { address: { city } } = person;
	//   console.log(city); // 输出: New York
	// function handleEvent({ target: { value } }) {
	// 	console.log(value);
	//   }
	//   // 模拟一个事件对象
	//   const event = {
	// 	target: {
	// 	  value: 'Hello, World!'
	// 	}
	//   };
	//   // 调用函数，直接解构事件对象
	//   handleEvent(event); // 输出: Hello, World!
	const onChange = useCallback(
		({ target: { value } }: React.ChangeEvent<SupportedElements>) => setValue(value),
		[]
	);
	return [value, onChange, setValue];
}
// 原生 JavaScript 不需要类型别名，因此省略 SupportedElements
// export default function (state = "") {
//   // useState 不需要类型注解
//   const [value, setValue] = useState(state);
//   // useCallback 不需要类型注解
//   const onChange = useCallback(
//     (event) => {
//       const { value } = event.target; // 解构赋值
//       setValue(value);
//     },
//     [] // 依赖项数组为空，表示只在挂载时创建一次
//   );
//   // 返回一个数组（元组），包含状态值、事件处理函数和设置状态的函数
//   return [value, onChange, setValue];
// }


// 作用：这是一个自定义的 React Hook，用于管理输入元素的状态。它提供了一个方便的方式来处理输入框（如文本框、选择框）的状态和变化。
// 使用场景：适用于任何需要管理输入状态的表单组件中。开发者可以通过这个 Hook 快速获取输入值和绑定更改事件处理程序，而无需手动管理 useState 和 onChange 逻辑。
// 注意点：
// 确保输入元素支持的类型正确地传递给 Hook。
// 在使用多个输入元素时，每个元素应使用自己的 useInputState 实例来独立管理状态。


// `HTMLInputElement` 和 `HTMLSelectElement` 是 TypeScript 中预定义的接口（Interface），它们表示特定的 HTML 元素类型。这些类型来自 TypeScript 的 DOM 类型声明，是 TypeScript 为了提供对浏览器 API 的强类型支持而定义的。

// ### 1. **`HTMLInputElement` 和 `HTMLSelectElement` 的定义**

// - **`HTMLInputElement`**: 代表 HTML `<input>` 元素的类型。它包含了 `<input>` 元素的所有属性和方法。例如，`value` 属性用于获取或设置输入框的值，`checked` 属性用于获取或设置复选框或单选按钮的选中状态等。

// - **`HTMLSelectElement`**: 代表 HTML `<select>` 元素的类型。它包含了 `<select>` 元素的所有属性和方法。例如，`value` 属性用于获取或设置选中选项的值，`options` 属性用于访问 `<select>` 元素中的选项集合等。

// ### 2. **这些类型从哪里来？**

// 这些类型是 TypeScript 内置的，定义在 TypeScript 的 DOM 类型声明文件（通常是 `lib.dom.d.ts`）中。TypeScript 提供了一组标准的类型定义文件，这些文件描述了各种浏览器 API 和全局对象。

// 这些类型定义文件是 TypeScript 的一部分，它们使得 TypeScript 能够提供对浏览器内置对象和 API 的类型检查。例如，`HTMLInputElement` 和 `HTMLSelectElement` 类型确保了我们在操作这些 DOM 元素时具有正确的类型信息和方法提示。

// ### 3. **其他类似的 HTML 元素类型**

// TypeScript 提供了许多其他的 HTML 元素类型，每种类型都代表一个特定的 HTML 元素。以下是一些常见的 HTML 元素类型：

// - **`HTMLButtonElement`**: 代表 `<button>` 元素的类型。
// - **`HTMLAnchorElement`**: 代表 `<a>`（锚点）元素的类型。
// - **`HTMLDivElement`**: 代表 `<div>` 元素的类型。
// - **`HTMLSpanElement`**: 代表 `<span>` 元素的类型。
// - **`HTMLTextAreaElement`**: 代表 `<textarea>` 元素的类型。
// - **`HTMLImageElement`**: 代表 `<img>` 元素的类型。
// - **`HTMLFormElement`**: 代表 `<form>` 元素的类型。
// - **`HTMLTableElement`**: 代表 `<table>` 元素的类型。
// - **`HTMLCanvasElement`**: 代表 `<canvas>` 元素的类型。
// - **`HTMLVideoElement`**: 代表 `<video>` 元素的类型。
// - **`HTMLAudioElement`**: 代表 `<audio>` 元素的类型。

// ### 4. **使用示例**

// 使用这些类型可以更精确地操作 DOM 元素，并确保代码的类型安全。例如：

// ```typescript
// function handleInputChange(element: HTMLInputElement) {
//   console.log(element.value); // `value` 是 `HTMLInputElement` 的一个属性
// }

// function handleSelectChange(element: HTMLSelectElement) {
//   console.log(element.selectedIndex); // `selectedIndex` 是 `HTMLSelectElement` 的一个属性
// }

// // 创建 DOM 元素
// const input = document.createElement('input');
// const select = document.createElement('select');

// // 使用特定类型的函数
// handleInputChange(input);  // 正确使用
// handleSelectChange(select); // 正确使用
// ```

// ### 5. **为什么要使用这些类型？**

// 使用这些特定的 HTML 元素类型可以帮助开发者在编写 TypeScript 代码时获得更好的类型检查和代码提示。这些类型确保了你只能使用与特定元素类型兼容的方法和属性，从而减少了代码中的错误。例如，TypeScript 知道 `HTMLInputElement` 有一个 `value` 属性，而 `HTMLDivElement` 没有。

// ### 总结

// `HTMLInputElement` 和 `HTMLSelectElement` 是 TypeScript 提供的接口，代表特定的 HTML 元素类型。它们源自 TypeScript 的 DOM 类型声明文件，提供了对浏览器 API 的强类型支持。类似的，还有许多其他 HTML 元素类型，用于描述各种 HTML 元素的属性和方法。通过使用这些类型，开发者可以在 TypeScript 中获得更强的类型安全性和开发体验。