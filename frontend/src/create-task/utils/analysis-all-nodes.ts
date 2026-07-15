// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: GPL-3.0-or-later
import { AllNodesOptions } from '@common/type/batch-task';
import { useCreatorStore } from '../store';

export const analysisAllNodes = () =>
  window.app?.graphToPrompt().then((res) => {
    const { output } = res;

    const allNodesOptions: AllNodesOptions = [];

    Object.keys(output).forEach((id) => {
      const nodeInfo = output[id];
      const { class_type, inputs } = nodeInfo;
      const paramsList: AllNodesOptions[0]['paramsList'] = [];

      Object.keys(inputs).forEach((key) => {
        paramsList.push({
          label: key,
          // eslint-disable-next-line @typescript-eslint/ban-ts-comment
          // @ts-expect-error
          value: inputs[key],
          isLinked: typeof inputs[key] === 'object',
        });
      });

      // 节点在画布上的标题（用户可能重命名过），与类型不同时一并展示
      const nodeTitle = window.app?.graph.getNodeById(id)?.title;

      allNodesOptions.push({
        id,
        label:
          nodeTitle && nodeTitle !== class_type
            ? `#${id}: ${nodeTitle} (${class_type})`
            : `#${id}: ${class_type}`,
        paramsList,
      });
    });

    useCreatorStore.setState({
      allNodesOptions,
    });

    return {
      allNodesOptions,
    };
  });
