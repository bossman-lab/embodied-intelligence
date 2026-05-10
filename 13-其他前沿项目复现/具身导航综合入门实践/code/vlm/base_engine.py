"""
VLM 决策基类
============
封装 system prompt 构建、用户文本构建、回复解析、降级策略及日志记录。
子类只需实现 _call_model() 方法即可。
"""

import json
from datetime import datetime
import numpy as np


class BaseVLMDecisionEngine:
    """
    大模型决策引擎基类。

    子类需实现：
        _call_model(system_prompt, user_text, key_images) -> str
            调用底层模型，返回原始文本回复。
    """

    def __init__(self, config):
        self.cfg = config
        self.targets = config.TARGET_OBJECTS
        self.reasoning_log = []
        self.count = 0

    # ── 公开接口 ──────────────────────────────────────────────

    def make_decision(self, key_images, detection_summary, frontier_info,
                      visited_targets, nav_history, agent_pos) -> dict:
        """
        执行一次 VLM 决策。

        Returns
        -------
        dict: {action, target_index, reasoning, confidence}
        """
        self.count += 1
        system_prompt = self._build_system_prompt()
        user_text = self._build_user_text(
            agent_pos, visited_targets, detection_summary,
            frontier_info, nav_history
        )

        try:
            raw = self._call_model(system_prompt, user_text, key_images).strip()
            print(f"\n{'=' * 60}")
            print(f"[VLM 决策 #{self.count}] 原始回复:")
            print(raw)
            print(f"{'=' * 60}\n")
            decision = self._parse(raw)
        except Exception as e:
            print(f"[VLM Error] {e}")
            decision = self._fallback(detection_summary, frontier_info, visited_targets)

        self.reasoning_log.append({
            "decision_id": self.count,
            "agent_position": agent_pos.tolist() if isinstance(agent_pos, np.ndarray) else list(agent_pos),
            "detections_count": len(detection_summary) if detection_summary else 0,
            "frontiers_count": len(frontier_info) if frontier_info else 0,
            "decision": decision,
            "timestamp": datetime.now().isoformat(),
        })
        return decision

    def save_log(self, path: str):
        """将推理日志保存为 JSON 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.reasoning_log, f, ensure_ascii=False, indent=2)
        print(f"[LOG] 推理日志 -> {path}")

    # ── 子类需覆盖 ────────────────────────────────────────────

    def _call_model(self, system_prompt: str, user_text: str, key_images) -> str:
        raise NotImplementedError("子类必须实现 _call_model()")

    # ── 内部工具 ──────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        return f"""你是一个具身智能导航机器人的决策大脑。你的任务是在室内环境中找到以下全部目标物体: {self.targets}

你需要根据当前观察到的图像、YOLO检测结果（含物体3D坐标和距离）、可探索的前沿点，做出导航决策。

决策规则:
1. 如果检测到了目标物体且距离合理(< 8米), 优先导航到目标物体
2. 如果检测到多个目标物体, 选择最近的未访问目标
3. 如果没有检测到目标物体, 选择最优的前沿点进行探索
4. 选择前沿点时, 优先选择距离适中、朝向较大未探索区域的方向
5. 如果所有目标都已访问, 返回 "task_complete"

严格以以下JSON格式回复, 不要输出其他内容:
{{
    "thinking": "你的详细思考过程: 1)看到了什么 2)分析各选项 3)做出决策的理由",
    "action": "go_to_object" 或 "explore_frontier" 或 "task_complete",
    "target_index": 选择的目标在对应列表中的索引(从0开始),
    "confidence": 0到1之间的置信度
}}"""

    def _build_user_text(self, agent_pos, visited_targets,
                         detection_summary, frontier_info, nav_history) -> str:
        text = f"""## 第 {self.count} 次决策

### 当前状态
- Agent位置: [{agent_pos[0]:.2f}, {agent_pos[1]:.2f}, {agent_pos[2]:.2f}]
- 已访问目标: {visited_targets if visited_targets else '无'}
- 待寻找目标: {[t for t in self.targets if t not in visited_targets]}

### YOLO 检测结果 (原地旋转360°汇总)
"""
        if detection_summary:
            for i, d in enumerate(detection_summary):
                p = (f"[{d['world_pos'][0]:.2f}, {d['world_pos'][1]:.2f}, {d['world_pos'][2]:.2f}]"
                     if d.get("world_pos") else "未知")
                dist = f"{d['distance']:.2f}m" if d.get("distance") is not None else "未知"
                tag = "目标" if d["is_target"] else "非目标"
                text += f"  [{i}] {d['class']} (置信度:{d['confidence']:.2f}) 3D位置:{p} 距离:{dist} {tag}\n"
        else:
            text += "  当前旋转一圈未检测到任何物体\n"

        text += "\n### 可用前沿点\n"
        if frontier_info:
            for i, f in enumerate(frontier_info):
                text += (f"  [{i}] 位置:[{f['position'][0]:.2f}, {f['position'][1]:.2f}, "
                         f"{f['position'][2]:.2f}] 距离:{f['distance']:.2f}m\n")
        else:
            text += "  无可用前沿点\n"

        text += f"\n### 导航历史\n{nav_history}\n"
        return text

    def _parse(self, text: str) -> dict:
        """解析 VLM 输出的 JSON，失败时做关键词匹配兜底。"""
        l = text.find("{")
        r = text.rfind("}")
        if l != -1 and r != -1 and r > l:
            try:
                d = json.loads(text[l:r + 1])
                return {
                    "action": d.get("action", "explore_frontier"),
                    "target_index": d.get("target_index", 0),
                    "reasoning": d.get("thinking", ""),
                    "confidence": d.get("confidence", 0.5),
                }
            except Exception:
                pass

        if "go_to_object" in text:
            return {"action": "go_to_object", "target_index": 0,
                    "reasoning": text, "confidence": 0.5}
        if "task_complete" in text:
            return {"action": "task_complete", "target_index": -1,
                    "reasoning": text, "confidence": 0.5}
        return {"action": "explore_frontier", "target_index": 0,
                "reasoning": text, "confidence": 0.3}

    def _fallback(self, dets, fronts, visited) -> dict:
        """VLM 调用失败时的规则降级策略。"""
        if dets:
            tgts = [d for d in dets if d["is_target"] and d["class"] not in visited
                    and d.get("distance") is not None and d["distance"] < 8]
            if tgts:
                tgts.sort(key=lambda x: x["distance"])
                idx = dets.index(tgts[0])
                return {"action": "go_to_object", "target_index": idx,
                        "reasoning": f"[降级] 检测到 {tgts[0]['class']}", "confidence": 0.6}
        if fronts:
            return {"action": "explore_frontier", "target_index": 0,
                    "reasoning": "[降级] 无目标, 探索前沿", "confidence": 0.3}
        return {"action": "explore_frontier", "target_index": 0,
                "reasoning": "[降级] 随机探索", "confidence": 0.1}
