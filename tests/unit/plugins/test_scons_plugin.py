import pytest
from pydantic import ValidationError

from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.scons_plugin import SConsPlugin


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_get_build_snaps_and_packages(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == {"scons"}


def test_get_build_environment(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {
        "DESTDIR": str(part_info.part_install_dir)
    }


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        SConsPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"


def test_get_build_commands(part_info):
    properties = SConsPlugin.properties_class.unmarshal({"source": "."})
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["scons", "scons install"]


def test_get_build_commands_with_options(part_info):
    properties = SConsPlugin.properties_class.unmarshal(
        {"source": ".", "scons-options": ["a=1", "b=2"]}
    )
    plugin = SConsPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == ["scons a=1 b=2", "scons install a=1 b=2"]
