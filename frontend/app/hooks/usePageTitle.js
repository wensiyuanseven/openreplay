import { useEffect } from 'react';

export default function usePageTitle(title) {
	return useEffect(() => {
		document.title = title;
	}, [])
}


// 作用：这是一个自定义的 React Hook，用于设置网页的标题。它在组件加载时更改 document.title。
// 使用场景：适用于需要动态更改网页标题的场景，例如根据不同的页面或组件设置不同的标题。
// 注意点：
// 确保在适当的组件生命周期阶段（例如组件挂载时）更改标题。
// 注意依赖项为空数组 []，意味着标题只会在组件首次挂载时设置。如果需要响应变化，应在依赖项数组中加入相应的依赖。
