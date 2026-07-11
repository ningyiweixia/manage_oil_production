# 承包商运力报备测试数据

## 异常补录

这些数据可在“承包商运力报备 > 异常补录”中录入，用于验证列表、筛选、统计卡片、确认和工单查看。

| 承包商 | 队伍 | 报备日期 | 可用数量 | 状态 | 施工能力 | 补录原因 |
| --- | --- | --- | ---: | --- | --- | --- |
| 胜利井下作业公司 | 修井一队 | 2026-07-10 | 2 | 可用 | 通用作业、酸化 | 外部接口未返回，现场电话确认可用 |
| 华油工程服务公司 | 作业三队 | 2026-07-10 | 0 | 忙碌 | 通用作业 | 正在执行上修作业 |
| 长庆油服二厂项目部 | 酸化班组 | 2026-07-10 | 1 | 可用 | 通用作业、酸化、深井 | 临时补充酸化保障队伍 |
| 渤海钻修技术服务 | 大修二队 | 2026-07-10 | 0 | 忙碌 | 通用作业、大修资质 | 大修设备占用中 |
| 西北井下工程公司 | 压裂保障队 | 2026-07-11 | 1 | 可用 | 通用作业、压裂、防砂 | 次日保障队伍预报 |
| 辽河油服应急队 | 应急抢修队 | 2026-07-11 | 0 | 异常 | 通用作业 | 车辆故障，待恢复 |

## 外部系统返回样例

用于联调 `/api/capacities?report_date=2026-07-10` 这类外部接口响应。

```json
{
  "items": [
    {
      "external_system_id": "EXT-WORKOVER-101",
      "contractor_name": "胜利井下作业公司",
      "team_name": "修井一队",
      "report_date": "2026-07-10",
      "available_count": 2,
      "status": "AVAILABLE",
      "external_status": "AVAILABLE",
      "capability_tags": {
        "demo": true,
        "major_repair": false,
        "acidizing": true,
        "fracturing": false,
        "sand_control": false,
        "deep_well": false
      },
      "contact_name": "张队长",
      "contact_phone": "13800001001",
      "qualification_expire_at": "2027-12-31",
      "equipment_summary": "通井机2台，泵车1台，井控装备齐套"
    },
    {
      "external_system_id": "EXT-WORKOVER-102",
      "contractor_name": "华油工程服务公司",
      "team_name": "作业三队",
      "report_date": "2026-07-10",
      "available_count": 0,
      "status": "BUSY",
      "external_status": "BUSY",
      "capability_tags": {
        "demo": true,
        "major_repair": false,
        "acidizing": false,
        "fracturing": false,
        "sand_control": false,
        "deep_well": false
      },
      "contact_name": "李队长",
      "contact_phone": "13800001002",
      "qualification_expire_at": "2027-10-31",
      "equipment_summary": "常规修井设备1套"
    },
    {
      "external_system_id": "EXT-WORKOVER-103",
      "contractor_name": "渤海钻修技术服务",
      "team_name": "大修二队",
      "report_date": "2026-07-10",
      "available_count": 1,
      "status": "AVAILABLE",
      "external_status": "AVAILABLE",
      "capability_tags": {
        "demo": true,
        "major_repair": true,
        "acidizing": false,
        "fracturing": false,
        "sand_control": false,
        "deep_well": true
      },
      "contact_name": "王队长",
      "contact_phone": "13800001003",
      "qualification_expire_at": "2028-06-30",
      "equipment_summary": "大修机1台，井控装备1套"
    }
  ]
}
```

## 建议检查点

1. 报备日期选择 `2026-07-10` 时，列表应显示 4 条补录数据或外部同步数据。
2. 施工能力筛选“通用作业”应能查到所有带 `demo` 能力的队伍。
3. 施工能力筛选“大修资质”应只查到大修队伍。
4. 可用队伍数应按可用数量汇总，不是按记录条数统计。
5. 将一条记录确认后，同步状态应从“待确认”变为“已同步”。
6. 标记异常后，同步异常数应增加，队伍不应再用于派工。
