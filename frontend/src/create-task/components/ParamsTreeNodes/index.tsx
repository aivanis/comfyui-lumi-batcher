// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: GPL-3.0-or-later
import { useCallback, useMemo } from 'react';

import { TreeSelect } from '@arco-design/web-react';
import { IconStarFill } from '@arco-design/web-react/icon';

import './index.scss';
import { useCreatorStore } from '@src/create-task/store';
import {
  getFavoritedInputKey,
  getFavoritedInputs,
} from '@src/create-task/utils/get-favorited-inputs';

const TreeNode = TreeSelect.Node;

/** 自定义搜索文案挂在 TreeNode 上，供 filterTreeNode 使用（支持按节点名搜索参数） */
const searchProps = (searchText: string) =>
  ({ dataSearchText: searchText }) as unknown as Record<string, never>;

/**
 * 参数选择树的公共逻辑：
 * - 工作流中收藏的输入（Favorited inputs）排在最前面
 * - 支持按参数名或节点名（含节点标题）搜索
 */
export const useParamsTreeNodes = (
  getDisabled: (nodeId: string | number, internalName: string) => boolean,
) => {
  const allNodesOptions = useCreatorStore((state) => state.allNodesOptions);

  const sortedOptions = useMemo(() => {
    const favoritedInputs = getFavoritedInputs();
    const options = allNodesOptions
      .map((parent) => {
        const paramsList = parent.paramsList
          .filter((p) => !p.isLinked)
          .map((p) => ({
            ...p,
            isFavorite: favoritedInputs.has(
              getFavoritedInputKey(String(parent.id), p.label),
            ),
          }));
        paramsList.sort((a, b) => Number(b.isFavorite) - Number(a.isFavorite));
        return { ...parent, paramsList };
      })
      .filter((parent) => parent.paramsList.length > 0);
    options.sort(
      (a, b) =>
        Number(b.paramsList.some((p) => p.isFavorite)) -
        Number(a.paramsList.some((p) => p.isFavorite)),
    );
    return options;
  }, [allNodesOptions]);

  const filterTreeNode = useCallback(
    (inputText: string, node: any) =>
      String(node.props.dataSearchText ?? node.props.title ?? '')
        .toLowerCase()
        .indexOf(inputText.toLowerCase()) > -1,
    [],
  );

  /** 选中后的展示文案：参数名 + 所属节点 */
  const renderFormat = useCallback(
    (_node: unknown, value: string | { value?: string | number }) => {
      const raw =
        typeof value === 'string' ? value : String(value?.value ?? '');
      try {
        const parsed = JSON.parse(raw);
        const parent = allNodesOptions.find(
          (n) => String(n.id) === String(parsed.id),
        );
        return parent
          ? `${parsed.nodeLabel} (${parent.label})`
          : parsed.nodeLabel;
      } catch (e) {
        return raw;
      }
    },
    [allNodesOptions],
  );

  const treeNodes = useMemo(
    () =>
      sortedOptions.map((parent) => {
        const { id, label, paramsList } = parent;
        return (
          <TreeNode key={id} title={label} disabled {...searchProps(label)}>
            {paramsList.map((param) => (
              <TreeNode
                key={JSON.stringify({
                  id,
                  nodeLabel: param.label,
                })}
                title={
                  param.isFavorite ? (
                    <span className="params-tree-leaf">
                      {param.label}
                      <IconStarFill className="params-tree-leaf-star" />
                    </span>
                  ) : (
                    param.label
                  )
                }
                isLeaf
                disabled={getDisabled(id, param.label)}
                {...searchProps(`${param.label} ${label}`)}
              />
            ))}
          </TreeNode>
        );
      }),
    [sortedOptions, getDisabled],
  );

  return { treeNodes, filterTreeNode, renderFormat };
};
