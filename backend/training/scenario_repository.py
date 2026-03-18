"""训练场景库读取与冻结服务。"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from training.config_loader import model_copy, model_to_dict

SCENARIO_BANK_PATH_ENV = "TRAINING_SCENARIO_BANK_PATH"
DEFAULT_SCENARIO_BANK_PATH = Path(__file__).resolve().parent / "config" / "scenario_bank.json"


def _model_validate(model_cls: type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    """兼容 Pydantic v1 和 v2 的模型校验入口。"""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


class ScenarioOption(BaseModel):
    """场景内的预设选项定义。"""

    id: str
    label: str
    impact_hint: str = ""


class ScenarioDefinition(BaseModel):
    """完整场景定义。"""

    id: str
    title: str
    era_date: str = ""
    location: str = ""
    brief: str = ""
    mission: str = ""
    decision_focus: str = ""
    # 场景阶段标签用于推荐策略感知“开场/中段/高潮/收束”等剧情节奏。
    phase_tags: List[str] = Field(default_factory=list)
    target_skills: List[str] = Field(default_factory=list)
    risk_tags: List[str] = Field(default_factory=list)
    briefing: str = ""
    options: List[ScenarioOption] = Field(default_factory=list)
    completion_hint: str = ""


class ScenarioBankConfig(BaseModel):
    """场景库配置。"""

    version: str = "scenario_bank_v1"
    scenarios: List[ScenarioDefinition] = Field(default_factory=list)


def resolve_scenario_bank_path(path: str | Path | None = None) -> Path:
    """解析场景库文件路径。"""
    if path:
        return Path(path).expanduser().resolve()

    env_path = os.getenv(SCENARIO_BANK_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_SCENARIO_BANK_PATH


def load_scenario_bank_config(path: str | Path | None = None) -> ScenarioBankConfig:
    """加载并校验场景库配置。"""
    resolved_path = resolve_scenario_bank_path(path)
    with resolved_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return _model_validate(ScenarioBankConfig, payload)


@lru_cache(maxsize=1)
def get_scenario_bank_config() -> ScenarioBankConfig:
    """获取缓存后的场景库配置。"""
    return load_scenario_bank_config()


def reset_scenario_bank_config_cache() -> None:
    """清理场景库缓存，供测试使用。"""
    get_scenario_bank_config.cache_clear()


class ScenarioRepository:
    """负责场景定义读取、查找与会话冻结。"""

    def __init__(self, scenario_bank: ScenarioBankConfig | None = None):
        self._scenario_bank = model_copy(scenario_bank or get_scenario_bank_config())
        self._scenario_map = {
            scenario.id: model_to_dict(scenario)
            for scenario in self._scenario_bank.scenarios
        }

    @property
    def version(self) -> str:
        """返回当前场景库版本。"""
        return self._scenario_bank.version

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """按场景 ID 获取完整定义。"""
        scenario = self._scenario_map.get(str(scenario_id))
        if scenario is None:
            return None
        return dict(scenario)

    def freeze_sequence(self, scenario_sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """把会话使用的场景序列冻结为完整快照。"""
        frozen_sequence: List[Dict[str, Any]] = []
        for item in scenario_sequence or []:
            if not isinstance(item, dict):
                continue

            scenario_id = str(item.get("id") or "").strip()
            if not scenario_id:
                continue

            scenario_payload = self.get_scenario(scenario_id) or {"id": scenario_id, "title": scenario_id}

            # 允许调用方覆盖标题等轻量元数据，但完整场景结构仍由场景库补齐。
            overlay = {key: value for key, value in item.items() if value is not None}
            scenario_payload.update(overlay)
            scenario_payload.setdefault("title", scenario_id)
            scenario_payload.setdefault("phase_tags", [])
            scenario_payload.setdefault("target_skills", [])
            scenario_payload.setdefault("risk_tags", [])
            scenario_payload.setdefault("options", [])
            frozen_sequence.append(scenario_payload)

        return frozen_sequence

    def build_summary_sequence(self, scenario_payload_sequence: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """从完整场景快照中提取摘要序列。"""
        summary_sequence: List[Dict[str, str]] = []
        for item in scenario_payload_sequence or []:
            if not isinstance(item, dict):
                continue
            scenario_id = str(item.get("id") or "").strip()
            if not scenario_id:
                continue
            summary_sequence.append(
                {
                    "id": scenario_id,
                    "title": str(item.get("title") or scenario_id),
                }
            )
        return summary_sequence
