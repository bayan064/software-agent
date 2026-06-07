# 订单与支付子系统架构设计说明

## 1. 需求概述
本模块负责处理电商系统中的订单创建、价格计算以及模拟支付流程。系统需要保证订单状态流转的正确性，并能对异常库存或支付失败进行处理。

## 2. 核心业务规则
- **创建订单**：输入用户ID、商品ID列表及数量。初始状态为 `PENDING`（待支付）。
- **计算价格**：订单总价 = 各商品单价 * 数量。如果总价超过 100 元，享受 9 折优惠。
- **支付订单**：用户调用支付接口。支付成功后状态变为 `PAID`；若支付超时或余额不足导致失败，状态变为 `FAILED`。

## 3. 接口契约约束
代码实现必须包含 `OrderSystem` 类，并对外提供以下三个核心方法：
1. `create_order(user_id: str, items: list) -> dict`
2. `calculate_total(order_id: str) -> float`
3. `pay_order(order_id: str, payment_method: str) -> bool`