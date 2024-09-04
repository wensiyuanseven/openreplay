import React from 'react';
import { connect } from 'react-redux';
import { NoContent } from 'UI';
import { remove, edit, init } from 'Duck/integrations/teams';
import DocLink from 'Shared/DocLink/DocLink';

function TeamsChannelList(props: { list: any, edit: (inst: any) => any, onEdit: () => void }) {
    const { list } = props;
    // Record 是一个内置的泛型工具类型，它用于构造一个对象类型，其中所有属性的键类型为 K，属性的值类型为 T
    // string：在 Record<string, any> 中，string 表示对象的键必须是字符ƒ串类型。
    // any：在 Record<string, any> 中，any 表示对象的值可以是任何类型。
    // 所以，Record<string, any> 实际上表示一个键为字符串类型、值可以为任何类型的对象。
    // todo 自己如何实现呢？
    const onEdit = (instance: Record<string, any>) => {
        props.edit(instance);
        props.onEdit();
    };

    return (
        <div className="mt-6">
            <NoContent
                title={
                    <div className="p-5 mb-4">
                        <div className="text-base text-left">
                            Integrate MS Teams with OpenReplay and share insights with the rest of the team, directly from the recording page.
                        </div>
                        <DocLink className="mt-4 text-base" label="Integrate MS Teams" url="https://docs.openreplay.com/integrations/msteams" />
                    </div>
                }
                size="small"
                show={list.size === 0}
            >
                {list.map((c: any) => (
                    <div
                        key={c.webhookId}
                        className="border-t px-5 py-2 flex items-center justify-between cursor-pointer hover:bg-active-blue"
                        onClick={() => onEdit(c)}
                    >
                        <div className="flex-grow-0" style={{ maxWidth: '90%' }}>
                            <div>{c.name}</div>
                            <div className="truncate test-xs color-gray-medium">{c.endpoint}</div>
                        </div>
                    </div>
                ))}
            </NoContent>
        </div>
    );
}

export default connect(
    (state: any) => ({
        list: state.getIn(['teams', 'list']),
    }),
    { remove, edit, init }
)(TeamsChannelList);
