from enum import Enum

from django.db import transaction
from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.api.viewsets.asset import AssetViewSet
from care.facility.models import Asset, AssetLocation, User, UserDefaultAssetLocation
from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedAssetListKeys(Enum):
    ID = "id"
    NAME = "name"
    ASSET_CLASS = "asset_class"
    IS_WORKING = "is_working"
    LOCATION_OBJECT = "location_object"


class ExpectedLocationObjectKeys(Enum):
    ID = "id"
    FACILITY = "facility"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    LOCATION_TYPE = "location_type"


class ExpectedFacilityKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedAssetRetrieveKeys(Enum):
    ID = "id"
    STATUS = "status"
    ASSET_TYPE = "asset_type"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    DESCRIPTION = "description"
    ASSET_CLASS = "asset_class"
    IS_WORKING = "is_working"
    NOT_WORKING_REASON = "not_working_reason"
    SERIAL_NUMBER = "serial_number"
    WARRANTY_DETAILS = "warranty_details"
    META = "meta"
    VENDOR_NAME = "vendor_name"
    SUPPORT_NAME = "support_name"
    SUPPORT_PHONE = "support_phone"
    SUPPORT_EMAIL = "support_email"
    QR_CODE_ID = "qr_code_id"
    MANUFACTURER = "manufacturer"
    WARRANTY_AMC_END_OF_VALIDITY = "warranty_amc_end_of_validity"
    LAST_SERVICED_ON = "last_serviced_on"
    NOTES = "notes"


class AssetViewSetTestCase(TestBase, TestClassMixin):
    endpoint = "/api/v1/asset/"
    asset_id = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        state = cls.create_state()
        district = cls.create_district(state=state)
        cls.user = cls.create_user(district=district, username="test user")
        facility = cls.create_facility(district=district, user=cls.user)
        cls.asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=facility
        )
        cls.asset = Asset.objects.create(
            name="Test Asset", current_location=cls.asset1_location, asset_type=50
        )

    def setUp(self):
        # Refresh token to header
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_assets(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedAssetListKeys]

        data = response.json()["results"][0]

        self.assertCountEqual(data.keys(), expected_keys)
        location_object_keys = [key.value for key in ExpectedLocationObjectKeys]
        self.assertCountEqual(data["location_object"].keys(), location_object_keys)
        facility_keys = [key.value for key in ExpectedFacilityKeys]
        self.assertCountEqual(data["location_object"]["facility"].keys(), facility_keys)

        # Ensure the data is coming in correctly
        data = response.json()["results"][0]
        self.assertIsInstance(data["id"], str)
        self.assertEqual(data["name"], "Test Asset")
        self.assertEqual(data["asset_class"], None)
        self.assertEqual(data["is_working"], None)
        self.assertIsInstance(data["location_object"]["id"], str)
        self.assertIsInstance(data["location_object"]["facility"]["id"], str)
        self.assertEqual(data["location_object"]["facility"]["name"], "Foo")
        self.assertIsInstance(data["location_object"]["created_date"], str)
        self.assertIsInstance(data["location_object"]["modified_date"], str)
        self.assertEqual(data["location_object"]["name"], "asset1 location")
        self.assertEqual(data["location_object"]["description"], "")
        self.assertEqual(data["location_object"]["location_type"], 1)

    def test_create_asset(self):
        sample_data = {
            "name": "Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "create"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_asset(self):
        response = self.client.get(f"{self.endpoint}{self.asset.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check if the expected keys are coming in the json response
        expected_keys = [key.value for key in ExpectedAssetRetrieveKeys]
        self.assertCountEqual(data.keys(), expected_keys)

        self.assertIsInstance(data["id"], int)
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["asset_type"], "INTERNAL")
        self.assertIsInstance(data["created_date"], str)
        self.assertIsInstance(data["modified_date"], str)
        self.assertEqual(data["name"], "Test Asset")
        self.assertEqual(data["description"], "")
        self.assertIsNone(data["asset_class"])
        self.assertIsNone(data["is_working"])
        self.assertIsNone(data["not_working_reason"])
        self.assertIsNone(data["serial_number"])
        self.assertEqual(data["warranty_details"], "")
        self.assertEqual(data["meta"], {})
        self.assertIsNone(data["vendor_name"])
        self.assertIsNone(data["support_name"])
        self.assertEqual(data["support_phone"], "")
        self.assertIsNone(data["support_email"])
        self.assertIsNone(data["qr_code_id"])
        self.assertIsNone(data["manufacturer"])
        self.assertIsNone(data["warranty_amc_end_of_validity"])
        self.assertIsNone(data["last_serviced_on"])
        self.assertEqual(data["notes"], "")

    def test_update_asset(self):
        sample_data = {
            "name": "Updated Test Asset",
            "current_location": self.asset1_location.pk,
            "asset_type": 50,
            "location": self.asset1_location.external_id,
        }
        response = self.new_request(
            (f"{self.endpoint}{self.asset.external_id}", sample_data, "json"),
            {"patch": "partial_update"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_data["name"])
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, sample_data["name"])

    def test_delete_asset(self):
        with transaction.atomic():
            response = self.new_request(
                (f"{self.endpoint}{self.asset.external_id}",),
                {"delete": "destroy"},
                AssetViewSet,
                self.user,
                {"external_id": self.asset.external_id},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), True)
        self.user.user_type = User.TYPE_VALUE_MAP["DistrictAdmin"]
        self.user.save()
        response = self.new_request(
            (f"{self.endpoint}{self.asset.external_id}",),
            {"delete": "destroy"},
            AssetViewSet,
            self.user,
            {"external_id": self.asset.external_id},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Asset.objects.filter(pk=self.asset.pk).exists(), False)

    def test_set_default_user_location_invalid_location(self):
        # tests invalid location
        sample_data = {"location": "invalid_location_id"}

        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # tests providing no location
        sample_data = {}
        response = self.new_request(
            (self.endpoint, sample_data, "json"),
            {"post": "set_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"location": "is required"})

    def test_get_default_user_location(self):
        UserDefaultAssetLocation.objects.create(
            user=self.user, location=self.asset1_location
        )
        response = self.new_request(
            (self.endpoint,),
            {"get": "get_default_user_location"},
            AssetViewSet,
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.asset1_location.external_id)
