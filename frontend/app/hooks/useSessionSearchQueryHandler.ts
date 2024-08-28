// 作用：这是一个自定义的 React Hook，用于处理会话搜索查询。它管理 URL 查询参数与应用状态之间的同步，用于根据查询参数更新过滤器，并在状态变化时更新 URL。
// 使用场景：适用于需要通过 URL 查询参数控制搜索或筛选行为的应用程序部分，尤其是在需要与 React Router 集成的场景中。
// 注意点：
// 确保在异步操作完成之前不会触发新的状态更新，避免可能的 race condition。
// 需要注意依赖数组中的依赖项，确保在适当的状态变化时重新执行逻辑。


import { useEffect, useState } from 'react';
import { useHistory } from 'react-router';
import { createUrlQuery, getFiltersFromQuery } from 'App/utils/search';

interface Props {
  onBeforeLoad?: () => Promise<any>;
  appliedFilter: any;
  applyFilter: any;
  loading: boolean;
}

const useSessionSearchQueryHandler = (props: Props) => {
  const [beforeHookLoaded, setBeforeHookLoaded] = useState(!props.onBeforeLoad);
  const { appliedFilter, applyFilter, loading } = props;
  const history = useHistory();

  useEffect(() => {
    const applyFilterFromQuery = async () => {
      if (!loading) {
        if (props.onBeforeLoad) {
          await props.onBeforeLoad();
          setBeforeHookLoaded(true);
        }
        const filter = getFiltersFromQuery(history.location.search, appliedFilter);
        applyFilter(filter, true, false);
      }
    };

    void applyFilterFromQuery();
  }, [loading]);

  useEffect(() => {
    const generateUrlQuery = () => {
      if (!loading && beforeHookLoaded) {
        const search: any = createUrlQuery(appliedFilter);
        history.replace({ search });
      }
    };

    generateUrlQuery();
  }, [appliedFilter, loading, beforeHookLoaded]);

  return null;
};

export default useSessionSearchQueryHandler;
