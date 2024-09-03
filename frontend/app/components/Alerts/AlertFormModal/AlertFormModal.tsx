import React, { useEffect, useState } from 'react';
import { SlideModal } from 'UI';
import { useStore } from 'App/mstore'
// todo
// observer 是 mobx-react-lite 库中的一个高阶函数，用于将 React 组件转换为观察者组件 这个观察者组件能够自动响应 MobX 状态树中的状态变化，并在状态改变时重新渲染组件
import { observer } from 'mobx-react-lite'
import AlertForm from '../AlertForm';
import { SLACK, TEAMS, WEBHOOK } from 'App/constants/schedule';
import { confirm } from 'UI';

// 定义接口 用于描述对象的结构，即对象应该有哪些属性、这些属性的类型是什么
interface Select {
    label: string;
    value: string | number
}


interface Props {
    showModal?: boolean;
    metricId?: number;
    onClose?: () => void;
}

// 函数参数类型注解
function AlertFormModal(props: Props) {
    const { alertsStore, settingsStore } = useStore()
    const { metricId = null, showModal = false } = props;
    const [showForm, setShowForm] = useState(false);
    const webhooks = settingsStore.webhooks
    useEffect(() => {
        settingsStore.fetchWebhooks();
    }, []);

    // 类型注解 表示一个数组，数组中的每个元素都必须是 Select 类型。也就是说，数组中的每个元素都是一个对象，这个对象必须有 label 和 value 属性，且 label 是字符串类型，value 是字符串或数字类型
    const slackChannels: Select[] = []
    const hooks: Select[] = []
    const msTeamsChannels: Select[] = []

    webhooks.forEach((hook) => {
        const option = { value: hook.webhookId, label: hook.name }
        if (hook.type === SLACK) {
            slackChannels.push(option)
        }
        if (hook.type === WEBHOOK) {
            hooks.push(option)
        }
        if (hook.type === TEAMS) {
            msTeamsChannels.push(option)
        }
    })

    const saveAlert = (instance) => {
        const wasUpdating = instance.exists();
        alertsStore.save(instance).then(() => {
            if (!wasUpdating) {
                toggleForm(null, false);
            }
            if (props.onClose) {
                props.onClose();
            }
        });
    };

    const onDelete = async (instance) => {
        if (
            await confirm({
                header: 'Confirm',
                confirmButton: 'Yes, delete',
                confirmation: `Are you sure you want to permanently delete this alert?`,
            })
        ) {
            alertsStore.remove(instance.alertId).then(() => {
                toggleForm(null, false);
            });
        }
    };

    const toggleForm = (instance, state) => {
        if (instance) {
            alertsStore.init(instance);
        }
        return setShowForm(state ? state : !showForm);
    };

    return (
        <AlertForm
            metricId={metricId}
            edit={alertsStore.edit}
            slackChannels={slackChannels}
            msTeamsChannels={msTeamsChannels}
            webhooks={hooks}
            onSubmit={saveAlert}
            onClose={props.onClose}
            onDelete={onDelete}
        />
    );
}

export default observer(AlertFormModal);
