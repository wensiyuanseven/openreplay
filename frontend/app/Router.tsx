// useEffect用于在组件挂载、更新或卸载时执行副作用，useRef用于创建可以在组件的整个生命周期中保持不变的引用。
import React, { useEffect, useRef } from 'react';
import { withRouter, RouteComponentProps } from 'react-router-dom';
import { connect, ConnectedProps } from 'react-redux';
import { Loader } from 'UI';
import { fetchUserInfo, setJwt } from 'Duck/user';
import { fetchList as fetchSiteList } from 'Duck/site';
import { withStore } from 'App/mstore';
import { Map } from 'immutable';

import * as routes from './routes';
import { fetchTenants } from 'Duck/user';
import { setSessionPath } from 'Duck/sessions';
import { ModalProvider } from 'Components/Modal';
import { GLOBAL_DESTINATION_PATH, IFRAME, JWT_PARAM } from 'App/constants/storageKeys';
import PublicRoutes from 'App/PublicRoutes';
import Layout from 'App/layout/Layout';
import { fetchListActive as fetchMetadata } from 'Duck/customField';
import { init as initSite } from 'Duck/site';
import PrivateRoutes from 'App/PrivateRoutes';
import { checkParam } from 'App/utils';
import IFrameRoutes from 'App/IFrameRoutes';
import { ModalProvider as NewModalProvider } from 'Components/ModalContext';

interface RouterProps extends RouteComponentProps, ConnectedProps<typeof connector> {
    isLoggedIn: boolean;
    sites: Map<string, any>;
    loading: boolean;
    changePassword: boolean;
    isEnterprise: boolean;
    fetchUserInfo: () => any;
    fetchTenants: () => any;
    setSessionPath: (path: any) => any;
    fetchSiteList: (siteId?: number) => any;
    match: {
        params: {
            siteId: string;
        }
    };
    mstore: any;
    setJwt: (jwt: string) => any;
    fetchMetadata: (siteId: string) => void;
    initSite: (site: any) => void;
}
// Router在这里是一个 React 组件。在这个文件中，Router 是一个函数式组件。
// C 是 Function Component 的缩写。在 React 中，FC 表示函数组件（Function Component），这是 React 中一种用于定义组件的方式。
// 函数组件定义
// const Router: React.FC<RouterProps> = (props) => {
//  // 组件内部的实现
// };
// Router 被定义为一个 React.FC<RouterProps>，其中 React.FC 是 TypeScript 中的一个泛型类型，表示一个函数式组件（Function Component）。
// RouterProps 是这个组件的 props 类型定义，用于约束传递给该组件的属性，使其类型安全。
// https://gpt2good.com/c/da96af45-efff-428f-b144-8db0cb726f2a
// 这段代码是泛型在类型定义中的应用,泛型可以在函数参数、返回值类型、类属性、接口属性， 类型别名，接口，泛型在枚举，联合类型，映射类型，类的继承和约束中，回调函数和事件处理，工厂函数和依赖注入都能应用

// React.FC<RouterProps> 是泛型在类型定义中的应用，用于定义一个函数组件 Router，并指定其 props 类型为 RouterProps。
// 这里的泛型 RouterProps 帮助 TypeScript 进行类型检查，确保传递给 Router 组件的 props 符合 RouterProps 的结构。
// 例子：定义一个函数组件 MyComponent
// 假设我们要创建一个简单的 React 函数组件 MyComponent，它接收 props 并显示一个标题和描述。我们使用 TypeScript 来确保 props 的类型正确。
// 1. 定义 props 的类型
// 首先，我们定义一个接口 MyComponentProps，描述这个组件的 props 结构。

// typescript
// 复制代码
// interface MyComponentProps {
//     title: string;
//     description: string;
// }
// MyComponentProps：这个接口定义了 props 对象的类型，要求 title 和 description 都是 string 类型。
// 2. 使用 React.FC 定义组件
// 现在我们使用 React.FC 泛型来定义 MyComponent 组件，并将 MyComponentProps 作为泛型参数传递给 React.FC。

// typescript
// 复制代码
// const MyComponent: React.FC<MyComponentProps> = (props) => {
//     return (
//         <div>
//             <h1>{props.title}</h1>
//             <p>{props.description}</p>
//         </div>
//     );
// };
// const MyComponent: React.FC<MyComponentProps>：我们使用 React.FC<MyComponentProps> 作为 MyComponent 的类型，这意味着 MyComponent 必须接收 MyComponentProps 类型的 props。

// (props)：这是函数组件的参数，它是 MyComponentProps 类型，因此 props.title 和 props.description 都是字符串。

// 3. 使用组件
// 最后，我们可以像这样使用 MyComponent 组件：

// typescript
// 复制代码
// <MyComponent title="Welcome" description="This is a description." />
// 当你使用 MyComponent 时，TypeScript 会检查你传递的 title 和 description 是否符合 MyComponentProps 的类型。如果你传递了错误的类型，TypeScript 会在编译时报错。
// 总结
// 定义 props 类型：首先定义一个接口 MyComponentProps，描述组件的 props。
// 使用 React.FC 泛型：使用 React.FC<MyComponentProps> 作为函数组件的类型注解，确保组件只能接收符合 MyComponentProps 的 props。
// 类型检查：当你使用这个组件时，TypeScript 会根据 MyComponentProps 进行类型检查，确保 props 的类型是正确的。

const Router: React.FC<RouterProps> = (props) => {
    // 组件内部实现
    const {
        isLoggedIn,
        siteId,
        sites,
        loading,
        location,
        fetchUserInfo,
        fetchSiteList,
        history,
        match: { params: { siteId: siteIdFromPath } },
        setSessionPath,
    } = props;
    const [isIframe, setIsIframe] = React.useState(false);
    const [isJwt, setIsJwt] = React.useState(false);

    const handleJwtFromUrl = () => {
        const urlJWT = new URLSearchParams(location.search).get('jwt');
        if (urlJWT) {
            props.setJwt(urlJWT);
        }
    };

    const handleDestinationPath = () => {
        if (!isLoggedIn && location.pathname !== routes.login()) {
            localStorage.setItem(GLOBAL_DESTINATION_PATH, location.pathname + location.search);
        }
    };

    const handleUserLogin = async () => {
        await fetchUserInfo();
        const siteIdFromPath = parseInt(location.pathname.split('/')[1]);
        await fetchSiteList(siteIdFromPath);
        props.mstore.initClient();

        const destinationPath = localStorage.getItem(GLOBAL_DESTINATION_PATH);
        if (
            destinationPath &&
            destinationPath !== routes.login() &&
            destinationPath !== routes.signup() &&
            destinationPath !== '/'
        ) {
            const url = new URL(destinationPath, window.location.origin);
            checkParams(url.search)
            history.push(destinationPath);
            localStorage.removeItem(GLOBAL_DESTINATION_PATH);
        }
    };

    const checkParams = (search?: string) => {
        const _isIframe = checkParam('iframe', IFRAME, search);
        const _isJwt = checkParam('jwt', JWT_PARAM, search);
        setIsIframe(_isIframe);
        setIsJwt(_isJwt);
    }

    useEffect(() => {
        checkParams();
        handleJwtFromUrl();
    }, []);

    useEffect(() => {
        // handleJwtFromUrl();
        handleDestinationPath();


        setSessionPath(previousLocation ? previousLocation : location);
    }, [location]);

    useEffect(() => {
        if (prevIsLoggedIn !== isLoggedIn && isLoggedIn) {
            handleUserLogin();
        }
    }, [isLoggedIn]);

    useEffect(() => {
        if (siteId && siteId !== lastFetchedSiteIdRef.current) {
            const activeSite = sites.find((s) => s.id == siteId);
            props.initSite(activeSite);
            props.fetchMetadata(siteId);
            lastFetchedSiteIdRef.current = siteId;
        }
    }, [siteId]);

    const lastFetchedSiteIdRef = useRef<any>(null);

    function usePrevious(value: any) {
        const ref = useRef();
        useEffect(() => {
            ref.current = value;
        }, [value]);
        return ref.current;
    }

    const prevIsLoggedIn = usePrevious(isLoggedIn);
    const previousLocation = usePrevious(location);

    const hideHeader = (location.pathname && location.pathname.includes('/session/')) ||
        location.pathname.includes('/assist/') || location.pathname.includes('multiview');

    if (isIframe) {
        return <IFrameRoutes isJwt={isJwt} isLoggedIn={isLoggedIn} loading={loading} />;
    }

    return isLoggedIn ? (
        <NewModalProvider>
            <ModalProvider>
                <Loader loading={loading || !siteId} className='flex-1'>
                    <Layout hideHeader={hideHeader} siteId={siteId}>
                        <PrivateRoutes />
                    </Layout>
                </Loader>
            </ModalProvider>
        </NewModalProvider>
    ) : <PublicRoutes />;
};

const mapStateToProps = (state: Map<string, any>) => {
    const siteId = state.getIn(['site', 'siteId']);
    const jwt = state.getIn(['user', 'jwt']);
    const changePassword = state.getIn(['user', 'account', 'changePassword']);
    const userInfoLoading = state.getIn(['user', 'fetchUserInfoRequest', 'loading']);
    const sitesLoading = state.getIn(['site', 'fetchListRequest', 'loading']);

    return {
        siteId,
        changePassword,
        sites: state.getIn(['site', 'list']),
        isLoggedIn: jwt !== null && !changePassword,
        loading: siteId === null || userInfoLoading || sitesLoading,
        email: state.getIn(['user', 'account', 'email']),
        account: state.getIn(['user', 'account']),
        organisation: state.getIn(['user', 'account', 'name']),
        tenantId: state.getIn(['user', 'account', 'tenantId']),
        tenants: state.getIn(['user', 'tenants']),
        isEnterprise:
            state.getIn(['user', 'account', 'edition']) === 'ee' ||
            state.getIn(['user', 'authDetails', 'edition']) === 'ee'
    };
};

const mapDispatchToProps = {
    fetchUserInfo,
    fetchTenants,
    setSessionPath,
    fetchSiteList,
    setJwt,
    fetchMetadata,
    initSite
};

const connector = connect(mapStateToProps, mapDispatchToProps);

export default withStore(withRouter(connector(Router)));
