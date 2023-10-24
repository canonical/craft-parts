import pytest
from craft_parts import errors
from craft_parts.utils import partition_utils


@pytest.mark.parametrize("partitions", [None, []])
def test_validate_partitions_success_feature_disabled(partitions):
    partition_utils.validate_partition_names(partitions)


@pytest.mark.parametrize(
    ("partitions", "message"),
    [
        (
            ["anything"],
            "Partitions are defined but partition feature is not enabled.",
        ),
    ],
)
def test_validate_partitions_failure_feature_disabled(partitions, message):
    with pytest.raises(errors.FeatureError) as exc_info:
        partition_utils.validate_partition_names(partitions)

    assert exc_info.value.message == message


@pytest.mark.usefixtures("enable_partitions_feature")
@pytest.mark.parametrize("partitions", [["default"], ["default", "mypart"]])
def test_validate_partitions_success_feature_enabled(partitions):
    partition_utils.validate_partition_names(partitions)


@pytest.mark.usefixtures("enable_partitions_feature")
@pytest.mark.parametrize(
    ("partitions", "message"),
    [
        ([], "Partition feature is enabled but no partitions are defined."),
        (["lol"], "First partition must be 'default'."),
        (["default", "default"], "Partitions must be unique."),
        (
            ["default", "!!!"],
            "Partition '!!!' must only contain lowercase letters.",
        ),
    ],
)
def test_validate_partitions_failure_feature_enabled(partitions, message):
    with pytest.raises(errors.FeatureError) as exc_info:
        partition_utils.validate_partition_names(partitions)

    assert exc_info.value.args[0] == message
