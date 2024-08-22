# 这个测试类 TestFeatureFlag 用于验证与特性标志（Feature Flags）相关的功能是否按预期工作。
# 具体来说，它测试了特性标志的条件和变体的准备工作以及各个数据模式（Schemas）的验证逻辑。通过这些单元测试，
# 确保代码在处理特性标志数据时的正确性和健壮性，尤其是在数据验证和处理阶段。
import json

from pydantic.error_wrappers import ValidationError

import schemas
from chalicelib.core.feature_flags import prepare_conditions_values, prepare_variants_values

class TestFeatureFlag:

# 描述: 测试 prepare_conditions_values 函数是否正确地将 FeatureFlagSchema 中的条件转换为期望的输出格式。
# 测试逻辑:
# 创建一个 FeatureFlagSchema 实例，包含两个条件。
# 预期输出是一个字典，其中每个条件的名称、发布百分比和过滤条件都被正确地序列化为字符串格式。
# 使用断言检查函数的输出是否与预期一致。
    def test_prepare_conditions_values(self):
        feature_flag_data = schemas.FeatureFlagSchema(
            flagKey="flag_2",
            conditions=[
                schemas.FeatureFlagCondition(
                    name="Condition 2",
                    rolloutPercentage=75,
                    filters=[{"key": "value1"}]
                ),
                schemas.FeatureFlagCondition(
                    name="Condition 3",
                    rolloutPercentage=25,
                    filters=[{"key": "value2"}]
                )
            ]
        )
        expected_output = {
            'condition_id_0': None,
            "name_0": "Condition 2",
            "rollout_percentage_0": 75,
            "filters_0": json.dumps([{"key": "value1"}]),
            'condition_id_1': None,
            "name_1": "Condition 3",
            "rollout_percentage_1": 25,
            "filters_1": json.dumps([{"key": "value2"}])
        }
        assert prepare_conditions_values(feature_flag_data) == expected_output
    # 描述: 测试 FeatureFlagSchema 的验证逻辑，确保在提供有效和无效数据时，能够正确地通过或抛出验证错误。
    # 测试逻辑:
    # 测试有效的 FeatureFlagSchema 数据，确保不会引发验证错误。
    # 测试缺少必需字段的无效数据，确保引发 ValidationError，并检查错误的详细信息
    def test_feature_flag_schema_validation(self):
        try:
            schemas.FeatureFlagSchema(
                flagKey="valid_flag",
                conditions=[
                    schemas.FeatureFlagCondition(name="Condition 1", rollout_percentage=50),
                    schemas.FeatureFlagCondition(name="Condition 2", rollout_percentage=25)
                ],
                variants=[
                    schemas.FeatureFlagVariant(value="Variant 1", rollout_percentage=50),
                    schemas.FeatureFlagVariant(value="Variant 2", rollout_percentage=50)
                ]
            )
        except ValidationError:
            assert False, "Valid data should not raise ValidationError"

        try:
            schemas.FeatureFlagSchema()
        except ValidationError as e:
            assert len(e.errors()) == 1
            for error in e.errors():
                assert error["type"] == "value_error.missing"
                assert error["loc"] in [("flagKey",)]
        else:
            assert False, "Invalid data should raise ValidationError"
    # 描述: 测试 FeatureFlagVariant 的验证逻辑，确保在提供有效和无效数据时，能够正确地通过或抛出验证错误。
    # 测试逻辑:
    # 测试有效的 FeatureFlagVariant 数据，确保不会引发验证错误。
    # 测试缺少必需字段的无效数据，确保引发 ValidationError，并检查错误的详细信息。
    def test_feature_flag_variant_schema_validation(self):
        try:
            schemas.FeatureFlagVariant(
                value="Variant Value",
                description="Variant Description",
                # payload={"key": "value"},
                rolloutPercentage=50
            )
        except ValidationError:
            assert False, "Valid data should not raise ValidationError"

        try:
            schemas.FeatureFlagVariant()
        except ValidationError as e:
            assert len(e.errors()) == 1
            error = e.errors()[0]
            assert error["type"] == "value_error.missing"
            assert error["loc"] == ("value",)
        else:
            assert False, "Invalid data should raise ValidationError"
    # 描述: 测试 FeatureFlagCondition 的验证逻辑，确保在提供有效和无效数据时，能够正确地通过或抛出验证错误。
    # 测试逻辑:
    # 测试有效的 FeatureFlagCondition 数据，确保不会引发验证错误。
    # 测试缺少必需字段的无效数据，确保引发 ValidationError，并检查错误的详细信息。
    def test_feature_flag_condition_schema_validation(self):
        try:
            schemas.FeatureFlagCondition(
                name="Condition Name",
                rolloutPercentage=50,
                filters=[{"key": "value"}]
            )
        except ValidationError:
            assert False, "Valid data should not raise ValidationError"

        try:
            schemas.FeatureFlagCondition()
        except ValidationError as e:
            assert len(e.errors()) == 1
            error = e.errors()[0]
            assert error["type"] == "value_error.missing"
            assert error["loc"] == ("name",)
        else:
            assert False, "Invalid data should raise ValidationError"
    # 描述: 测试 SearchFlagsSchema 的验证逻辑，确保在提供有效和无效数据时，能够正确地通过或抛出验证错误。
    # 测试逻辑:
    # 测试有效的 SearchFlagsSchema 数据，确保不会引发验证错误。
    # 测试包含超出限制的数字和无效枚举值的无效数据，确保引发 ValidationError，并检查错误的详细信息。
    def test_search_flags_schema_validation(self):
        try:
            schemas.SearchFlagsSchema(
                limit=15,
                user_id=123,
                order=schemas.SortOrderType.desc,
                query="search term",
                is_active=True
            )
        except ValidationError:
            assert False, "Valid data should not raise ValidationError"

        try:
            schemas.SearchFlagsSchema(
                limit=500,
                user_id=-1,
                order="invalid",
                query="a" * 201,
                isActive=None
            )
        except ValidationError as e:
            assert len(e.errors()) == 2
            assert e.errors()[0]["ctx"] == {'limit_value': 200}
            assert e.errors()[0]["type"] == "value_error.number.not_le"

            assert e.errors()[1]["msg"] == "value is not a valid enumeration member; permitted: 'ASC', 'DESC'"
            assert e.errors()[1]["type"] == "type_error.enum"
        else:
            assert False, "Invalid data should raise ValidationError"

    # 描述: 测试 prepare_variants_values 函数是否正确地处理单个变体的转换。
    # 测试逻辑:
    # 创建一个 FeatureFlagSchema 实例，其中包含一个变体。
    # 预期输出是一个字典，其中变体的值、描述、载荷（此处为null）和发布百分比被正确地转换和序列化。
    # 使用断言检查函数的输出是否与预期一致。
    def test_prepare_variants_values_single_variant(self):
        feature_flag_data = schemas.FeatureFlagSchema(
            flagKey="flag_1",
            variants=[
                schemas.FeatureFlagVariant(
                    value="Variant 1",
                    description="Description 1",
                    # payload="{'key': 'value1'}",
                    rolloutPercentage=50
                )
            ]
        )
        expected_output = {
            "v_value_0": "Variant 1",
            "v_description_0": "Description 1",
            # "payload_0": json.dumps({"key": "value1"}),
            'v_payload_0': 'null',
            "v_rollout_percentage_0": 50
        }
        assert prepare_variants_values(feature_flag_data) == expected_output

    # 描述: 测试 prepare_variants_values 函数是否正确地处理多个变体的转换。
    # 测试逻辑:
    # 创建一个 FeatureFlagSchema 实例，其中包含多个变体。
    # 预期输出是一个字典，其中每个变体的值、描述、载荷（此处为null）和发布百分比被正确地转换和序列化。
    # 使用断言检查函数的输出是否与预期一致。
    def test_prepare_variants_values_multiple_variants(self):
        feature_flag_data = schemas.FeatureFlagSchema(
            flagKey="flag_2",
            variants=[
                schemas.FeatureFlagVariant(
                    value="Variant 1",
                    description="Description 1",
                    # payload="{'key': 'value1'}",
                    rolloutPercentage=50
                ),
                schemas.FeatureFlagVariant(
                    value="Variant 2",
                    description="Description 2",
                    # payload="{'key': 'value1'}",
                    rolloutPercentage=50
                )
            ]
        )
        expected_output = {
            "v_value_0": "Variant 1",
            "v_description_0": "Description 1",
            # "payload_0": json.dumps({"key": "value1"}),
            'v_payload_0': 'null',
            "v_rollout_percentage_0": 50,
            "v_value_1": "Variant 2",
            "v_description_1": "Description 2",
            # "payload_1": json.dumps({"key": "value2"}),
            'v_payload_1': 'null',
            "v_rollout_percentage_1": 50
        }
        assert prepare_variants_values(feature_flag_data) == expected_output
