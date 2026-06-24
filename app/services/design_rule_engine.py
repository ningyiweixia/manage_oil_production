"""工程设计规则引擎。

方案要求：
- 拿到防偏磨和 A5 数据后先过一遍内置的规则库
- 如果参数互相冲突，直接阻断生成并弹窗报错
- 严禁"带病设计"
"""

import logging
from typing import Any

from app.schemas.engineering import RuleCheckResult

logger = logging.getLogger(__name__)


def _check_pump_depth_match(measures: dict[str, Any]) -> list[str]:
    """校验抽油机型号与深度是否匹配。

    规则：
    - 深度 > 3000m 必须使用特定型号抽油机
    """
    errors: list[str] = []
    depth = measures.get("well_depth", 0)
    pump_model = measures.get("pump_model", "")

    if depth and depth > 3000 and "型号" not in str(pump_model):
        errors.append(f"井深 {depth}m > 3000m，抽油机型号 {pump_model} 不匹配")

    return errors


def _check_measure_conflicts(measures: list[dict[str, Any]]) -> list[str]:
    """校验措施类型与井况是否矛盾。"""
    errors: list[str] = []
    measure_types = {m.get("measure_type", "") for m in measures if isinstance(m, dict)}

    if "acidizing" in measure_types and "sand_washing" in measure_types:
        errors.append("酸化和冲砂洗井不能在同一工序中同时进行")

    return errors


def _check_construction_params(measures: list[dict[str, Any]]) -> list[str]:
    """校验施工参数是否在合理范围。"""
    errors: list[str] = []
    for m in measures:
        if not isinstance(m, dict):
            continue
        params = m.get("construction_params", {}) or {}
        pressure = params.get("pressure", 0)
        temperature = params.get("temperature", 0)

        if pressure and (pressure < 0 or pressure > 100):
            errors.append(f"施工压力 {pressure}MPa 超出合理范围 (0-100MPa)")

        if temperature and (temperature < -50 or temperature > 500):
            errors.append(f"施工温度 {temperature}°C 超出合理范围 (-50~500°C)")

    return errors


def check_well_parameters(well_no: str, measures: dict[str, Any]) -> RuleCheckResult:
    """校验井参数与措施的合理性。

    Args:
        well_no: 井号
        measures: 修井措施 JSONB 数据

    Returns:
        校验结果
    """
    errors: list[str] = []
    warnings: list[str] = []

    measures_list = measures.get("measures", []) if isinstance(measures, dict) else []

    errors.extend(_check_pump_depth_match(measures))
    errors.extend(_check_measure_conflicts(measures_list))
    errors.extend(_check_construction_params(measures_list))

    if not measures_list:
        warnings.append("未包含修井措施数据，生成的文档可能不完整")

    return RuleCheckResult(passed=len(errors) == 0, errors=errors, warnings=warnings)


def check_fpm_data(well_no: str, fpm_params: dict[str, Any]) -> RuleCheckResult:
    """校验防偏磨参数。

    Args:
        well_no: 井号
        fpm_params: 防偏磨设计系统返回的参数

    Returns:
        校验结果
    """
    errors: list[str] = []

    if not fpm_params:
        errors.append(f"井号 {well_no} 未获取到防偏磨参数")
        return RuleCheckResult(passed=False, errors=errors)

    wear_level = fpm_params.get("wear_level", "")
    if wear_level and wear_level.upper() == "SEVERE":
        errors.append(f"井号 {well_no} 偏磨程度严重（{wear_level}），超出常规施工能力")

    required = ["casing_diameter", "tubing_size", "wear_level"]
    missing = [f for f in required if f not in fpm_params]
    if missing:
        errors.append(f"防偏磨参数不完整，缺少: {', '.join(missing)}")

    return RuleCheckResult(passed=len(errors) == 0, errors=errors)


def validate_design_before_generation(
    well_no: str,
    measures: dict[str, Any],
    fpm_params: dict[str, Any],
) -> RuleCheckResult:
    """综合校验 - 组合所有规则校验。

    方案要求：
    - 数据校验没问题后，才允许模板渲染
    - 如果参数互相冲突，直接阻断生成并报错

    Returns:
        校验结果，passed=False 时必须阻断生成
    """
    well_check = check_well_parameters(well_no, measures)
    fpm_check = check_fpm_data(well_no, fpm_params)

    all_errors = well_check.errors + fpm_check.errors
    all_warnings = well_check.warnings + fpm_check.warnings

    return RuleCheckResult(
        passed=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )
