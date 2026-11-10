#!/usr/bin/env python3
"""DecisionPivot-targeted category specification for the 20K augmentation tranche."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class CategorySpec:
    category_id: str
    family: str
    name_zh: str
    target: int
    difficulty: str


CATEGORIES: Tuple[CategorySpec, ...] = (
    CategorySpec("ledger_batch_total_error", "ledger_reconcile", "账本：批次总额错误", 575, "arithmetic_aggregation"),
    CategorySpec("log_actual_statement", "log_count_check", "日志计数：实际声明正确", 750, "filter_and_count"),
    CategorySpec("state_equality_failure", "state_goal", "状态目标：相同性条件失败", 525, "single_field_mismatch"),
    CategorySpec("record_derived_field", "record_rule", "记录规则：派生字段计算", 525, "derived_value"),
    CategorySpec("facts_multitable_subtraction", "answerable_facts", "事实判断：多表聚合后减法", 300, "multi_table_arithmetic"),
    CategorySpec("dependency_complex_closure", "dependency_resolution", "依赖解析：Level 3复杂依赖闭包", 775, "deep_graph_closure"),
    CategorySpec("policy_rule_precedence", "policy_case", "政策判断：规则优先级", 0, "ordered_rules"),
    CategorySpec("dependency_version_conflict", "dependency_resolution", "依赖解析：版本冲突", 550, "empty_version_intersection"),
    CategorySpec("record_field_scope", "record_rule", "记录规则：字段依赖范围", 475, "field_scope"),
    CategorySpec("log_both_boundaries", "log_count_check", "日志计数：同时处理起止边界", 825, "inclusive_exclusive_boundaries"),
    CategorySpec("dependency_exclusive_boundary", "dependency_resolution", "依赖解析：排除式版本边界", 550, "exclusive_semver_boundary"),
    CategorySpec("state_missing_step", "state_goal", "状态目标：关键步骤缺失", 575, "missing_transition"),
    CategorySpec("dependency_missing_item", "dependency_resolution", "依赖解析：依赖项缺失", 700, "missing_node"),
    CategorySpec("permission_three_level_tree", "permission_inheritance", "权限继承：三层权限树", 300, "deep_inheritance"),
    CategorySpec("policy_four_exceptions", "policy_case", "政策判断：四条例外规则", 325, "multiple_exceptions"),
    CategorySpec("permission_role_chain", "permission_inheritance", "权限继承：角色链", 250, "role_chain"),
    CategorySpec("dependency_self_constraint", "dependency_resolution", "依赖解析：包自身约束", 675, "root_constraint"),
    CategorySpec("triage_category_priority", "triage_order", "分诊排序：类别优先级", 600, "lexicographic_priority"),
    CategorySpec("state_wrong_object", "state_goal", "状态目标：目标对象错误", 550, "object_identity"),
    CategorySpec("dependency_runtime", "dependency_resolution", "依赖解析：运行时依赖", 550, "runtime_only_edge"),
    CategorySpec("facts_four_hop", "answerable_facts", "事实判断：Level 3四跳事实链", 325, "four_hop_graph"),
    CategorySpec("permission_level2", "permission_inheritance", "权限继承：Level 2", 325, "two_hop_inheritance"),
    CategorySpec("state_step_order", "state_goal", "状态目标：步骤顺序交换", 0, "non_commutative_steps"),
    CategorySpec("permission_level3", "permission_inheritance", "权限继承：Level 3", 325, "three_hop_inheritance"),
    CategorySpec("facts_two_level_inheritance", "answerable_facts", "事实判断：两层继承链", 275, "two_hop_graph"),
    CategorySpec("dependency_ordinary_boundary", "dependency_resolution", "依赖解析：普通版本边界", 625, "inclusive_semver_boundary"),
    CategorySpec("state_quantity_failure", "state_goal", "状态目标：数量条件失败", 375, "numeric_goal"),
    CategorySpec("facts_inheritance_reasoning", "answerable_facts", "事实判断：继承关系推理", 275, "inheritance_graph"),
    CategorySpec("permission_scope_change", "permission_inheritance", "权限继承：作用域变化", 250, "scope_override"),
    CategorySpec("permission_action_change", "permission_inheritance", "权限继承：操作权限变化", 450, "action_specific_permission"),
    CategorySpec("schedule_equipment", "schedule_conflict", "排期冲突：设备条件", 400, "equipment_constraint"),
    CategorySpec("log_off_by_one", "log_count_check", "日志计数：差1条", 500, "single_boundary_event"),
    CategorySpec("ledger_missing_entry", "ledger_reconcile", "账本核对：缺少条目", 600, "missing_transaction"),
    CategorySpec("clause_outside_condition", "clause_change", "条款变化：条件范围外", 600, "out_of_scope_change"),
    CategorySpec("state_content_failure", "state_goal", "状态目标：内容条件错误", 525, "content_goal"),
    CategorySpec("policy_exception_handling", "policy_case", "政策判断：需要处理例外", 325, "exception_override"),
    CategorySpec("ledger_fee_error", "ledger_reconcile", "账本核对：费用错误", 400, "fee_recalculation"),
    CategorySpec("clause_level3", "clause_change", "条款变化：Level 3", 325, "nested_clause_effect"),
    CategorySpec("permission_sealed_resource", "permission_inheritance", "权限继承：密封资源", 400, "sealed_resource_deny"),
    CategorySpec("filter_k_of_n", "filter_match", "条件筛选：k-of-n证书要求", 400, "threshold_constraints"),
    CategorySpec("ledger_date_error", "ledger_reconcile", "账本核对：日期错误", 450, "date_window"),
    CategorySpec("schedule_capacity", "schedule_conflict", "排期冲突：座位容量", 475, "capacity_constraint"),
    CategorySpec("filter_conditional_rule", "filter_match", "条件筛选：条件式规则", 400, "conditional_constraint"),
    CategorySpec("schedule_level3", "schedule_conflict", "排期冲突：Level 3", 275, "multi_constraint_schedule"),
    CategorySpec("filter_converted_minimum", "filter_match", "条件筛选：换算后的最小值", 325, "unit_conversion"),
)


CATEGORY_BY_ID: Dict[str, CategorySpec] = {spec.category_id: spec for spec in CATEGORIES}
TARGETS: Dict[str, int] = {spec.category_id: spec.target for spec in CATEGORIES}


def total_target() -> int:
    return sum(TARGETS.values())


if len(CATEGORY_BY_ID) != 45:
    raise RuntimeError("DecisionPivot category ids must be unique and total 45")
if total_target() != 20_000:
    raise RuntimeError(f"DecisionPivot augmentation target must total 20,000, got {total_target()}")
