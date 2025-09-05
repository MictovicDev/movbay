from typing import List, Dict, Any
from logistics.service import SpeedyDispatch
from .calculate_order_package import calculate_order_package
from rest_framework.response import Response
from rest_framework import status
from logistics.models import ShippingRate, Address, Parcel
from django.shortcuts import get_object_or_404
from stores.models import Product
from django.db import transaction
import logging
from stores.models import Order

logger = logging.getLogger(__name__)

def process_shipping_rates(rates_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and format shipping rates for frontend.

    Args:
        rates_data: List of raw shipping rate dictionaries from the dispatch service.

    Returns:
        List of processed rate dictionaries sorted by amount.
    """
    processed_rates = []

    for rate in rates_data:
        processed_rate = {
            'rate_id': rate.get('rate_id'),
            'carrier_name': rate.get('carrier_name'),
            'carrier_logo': rate.get('carrier_logo'),
            'amount': rate.get('amount'),
            'currency': rate.get('currency'),
            'delivery_time': rate.get('delivery_time'),
            'pickup_time': rate.get('pickup_time'),
            'service_description': rate.get('carrier_rate_description'),
            'dropoff_required': rate.get('dropoff_required', False),
            'includes_insurance': rate.get('includes_insurance', False),
            'recommended': rate.get('metadata', {}).get('recommended', False)
        }
        processed_rates.append(processed_rate)

    # Sort by amount (cheapest first)
    processed_rates.sort(key=lambda x: x['amount'])
    logger.debug("Processed shipping rates: %s", processed_rates)
    return processed_rates

def get_best_rate(rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Select the best shipping rate (recommended or cheapest).

    Args:
        rates: List of processed rate dictionaries.

    Returns:
        The best rate dictionary.
    """
    recommended_rate = next((r for r in rates if r.get("recommended")), None)
    return recommended_rate or min(rates, key=lambda r: r["amount"])

@transaction.atomic
def handle_speedy_dispatch(order: Order) -> Response:
    """Handle Speedy dispatch logic with proper error handling and database transactions.

    Args:
        user: The authenticated user.
        product_id: ID of the product being shipped.
        delivery_details: Dictionary containing delivery address details.
        order_items: Order items to calculate package details.

    Returns:
        Response: REST framework response with shipping rates or error message.
    """
    try:
        dispatch = SpeedyDispatch()
        order_items = order.order_items.all()
        # Step 1: Calculate package details
        payload = calculate_order_package(order_items)
        # logger.info("Package payload calculated for product %s", product_id)

        # Step 2: Create addresses
        pickup_result = dispatch.create_pickupaddress(order_id= order.id)
        if not pickup_result.get('status'):
            logger.error("Failed to create pickup address for product %s", order.id)
            return Response(
                {"status": "error", "error": "Failed to create pickup address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        pickup_address_id = pickup_result['data']['address_id']

        delivery_result = dispatch.create_deliveryaddress(order)
        if not delivery_result.get('status'):
            logger.error("Failed to create delivery address for product %s", order.id)
            return Response(
                {"status": "error", "error": "Failed to create delivery address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        delivery_address_id = delivery_result['data']['address_id']
        package_result = dispatch.create_package(payload)
        if not package_result.get('status'):
            logger.error("Failed to create package for product %s", order.order_id)
            return Response(
                {"status": "error", "error": "Failed to create package"},
                status=status.HTTP_400_BAD_REQUEST
            )

        parcel_result = dispatch.create_parcel(
            order_items,
            payload.get('weight'),
            package_result['data']['packaging_id']
        )
        if not parcel_result.get('status'):
            logger.error("Failed to create parcel for product %s", order.id)
            return Response(
                {"status": "error", "error": "Failed to create parcel"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 5: Get shipping rates
        rates_result = dispatch.get_shipping_rates(
            pickup_address_id,
            delivery_address_id,
            parcel_result['data']['parcel_id']
        )
        if not rates_result.get('status') or not rates_result.get('data'):
            logger.error("No shipping rates available for product %s", order.id)
            return Response(
                {"status": "error", "error": "No shipping rates available"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 6: Process rates and select best option
        rates = process_shipping_rates(rates_result['data'])
        best_rate = get_best_rate(rates)
        logger.info("Best rate selected for product %s: %s", order.id, best_rate)

        # Step 7: Save best rate to database
        # ShippingRate.objects.create(
        #     terminal_rate_id=best_rate['rate_id'],
        #     pickup_address=pickup_address,
        #     delivery_address=delivery_address,
        #     parcel=parcel,
        #     carrier_name=best_rate['carrier_name'],
        #     currency=best_rate['currency'],
        #     delivery_time=best_rate['delivery_time'],
        #     pickup_time=best_rate['pickup_time'],
        #     total=best_rate['amount']
        # )

        # Step 8: Return response
        return Response({
            "status": "success",
            "message": "Shipping rates retrieved successfully",
            "data": {
                "rates": rates,
                "pickup_address_id": pickup_address_id,
                "delivery_address_id": delivery_address_id,
                "parcel_id": parcel_result['data']['parcel_id']
            }
        }, status=status.HTTP_200_OK)

    except (ValueError, KeyError, Order.DoesNotExist) as e:
        logger.error("Speedy dispatch error for product %s: %s", order.id, str(e), exc_info=True)
        return Response(
            {"status": "error", "error": f"Speedy dispatch failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.critical("Unexpected error in speedy dispatch for product %s: %s", order.order_id, str(e), exc_info=True)
        return Response(
            {"status": "error", "error": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )