# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import logging
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest
import yaml
from charm import KafkaBrokerRackAwarenessCharm
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness

logger = logging.getLogger(__name__)

METADATA = str(yaml.safe_load(Path("./metadata.yaml").read_text()))


@pytest.fixture
def harness():
    harness = Harness(KafkaBrokerRackAwarenessCharm, meta=METADATA)
    harness.begin()
    return harness


def test_install_with_kafka(harness: Harness):
    with patch("charm.snap.Snap.present", new_callable=PropertyMock, return_value=True):
        harness.charm.on.install.emit()

    assert isinstance(harness.charm.unit.status, ActiveStatus)


def test_install_without_kafka(harness: Harness):
    with (
        patch("charm.snap.Snap.present", new_callable=PropertyMock, return_value=False),
        patch("ops.framework.EventBase.defer") as patched_defer,
    ):
        harness.charm.on.install.emit()

        patched_defer.assert_called()
        assert isinstance(harness.charm.unit.status, BlockedStatus)


def test_config_changed_valid(harness: Harness):
    # Install check succeeds and the unit is Active
    harness.charm.unit.status = ActiveStatus()
    with (
        patch("charm.safe_write_to_file", return_value=None) as patched_write,
        patch("charm.shutil.chown", return_value=None) as patched_chown,
    ):
        harness.update_config(key_values={"broker-rack": "us-west"})

        patched_write.assert_called_with(
            content="broker.rack=us-west",
            path="/var/snap/charmed-kafka/current/etc/kafka/rack.properties",
        )
        patched_chown.assert_called_with(
            "/var/snap/charmed-kafka/current/etc/kafka/rack.properties",
            user="snap_daemon",
            group="root",
        )


def test_config_changed_invalid(harness: Harness):
    # Install check fails and the unit is Blocked
    harness.charm.unit.status = BlockedStatus()
    with (
        patch("ops.framework.EventBase.defer") as patched_defer,
        patch("charm.safe_write_to_file", return_value=None) as patched_write,
        patch("charm.shutil.chown", return_value=None) as patched_chown,
    ):
        harness.update_config(key_values={"broker-rack": "us-west"})

        patched_write.assert_not_called()
        patched_chown.assert_not_called()
        patched_defer.assert_called()
