
# from django.dispatch import receiver
# from django.db.models.signals import post_save, post_delete, m2m_changed
# from apps.events.models import StockTransaction, TicketStock, ETicket, Order, Ticket, Event
# from apps.super_sellers.cache import bump_stats_version

# def _org_from_instance(instance):
#     try:
#         return instance.ticket_stock.seller.super_seller_id
#     except Exception:
#         pass
#     try:
#         return instance.seller.super_seller_id
#     except Exception:
#         pass
#     try:
#         return instance.related_order.item.ticket.event.organization_id
#     except Exception:
#         pass
#     try:
#         return instance.event.organization_id
#     except Exception:
#         pass
#     return None

# def _bump_if_org_found(instance):
#     org_id = _org_from_instance(instance)
#     if org_id:
#         bump_stats_version(org_id)

# @receiver(post_save, sender=StockTransaction)
# def on_stock_tx_change(sender, instance, **kwargs):
#     if instance.transaction_type == "SALE":
#         _bump_if_org_found(instance)

# @receiver(post_save, sender=TicketStock)
# def on_ticket_stock_change(sender, instance, **kwargs):
#     _bump_if_org_found(instance)

# @receiver(post_save, sender=ETicket)
# def on_eticket_create(sender, instance, created, **kwargs):
#     if created:
#         _bump_if_org_found(instance)

# @receiver(post_save, sender=Order)
# def on_order_change(sender, instance, **kwargs):
#     if instance.status in ("FINISHED",):
#         _bump_if_org_found(instance)
