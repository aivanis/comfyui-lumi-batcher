// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: GPL-3.0-or-later

/**
 * ComfyUI 的 “Favorited inputs” 存在工作流里：
 * graph.extra.favoritedWidgets.favorites = [{ nodeLocatorId, widgetName }]
 * 根图节点的 nodeLocatorId 就是节点 id，子图节点为 "子图uuid:局部id"。
 */
interface FavoritedWidget {
  nodeLocatorId?: string | number;
  widgetName?: string;
}

type GraphWithExtra = {
  extra?: {
    favoritedWidgets?: {
      favorites?: FavoritedWidget[];
    };
  };
};

export const getFavoritedInputKey = (
  nodeId: string | number,
  inputName: string,
): string => `${nodeId}::${inputName}`;

/** 读取当前工作流中收藏的输入，key 为 `${nodeId}::${inputName}` */
export const getFavoritedInputs = (): Set<string> => {
  const res = new Set<string>();

  try {
    const graph = window.app?.graph as unknown as GraphWithExtra | undefined;
    const favorites = graph?.extra?.favoritedWidgets?.favorites;
    if (Array.isArray(favorites)) {
      favorites.forEach((item) => {
        if (item?.nodeLocatorId != null && item?.widgetName != null) {
          res.add(
            getFavoritedInputKey(
              String(item.nodeLocatorId),
              String(item.widgetName),
            ),
          );
        }
      });
    }
  } catch (e) {
    console.error('Failed to read favorited inputs from workflow:', e);
  }

  return res;
};
