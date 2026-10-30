from copy import deepcopy


def _is_non_empty_str(val):
    return isinstance(val, str) and bool(val.strip())


def _is_non_neg_num(val):
    return not isinstance(val, bool) and isinstance(val, (int, float)) and val >= 0


def estimate_eta(order, partner, travel, now=0):
    if not isinstance(order, dict) or not isinstance(partner, dict) or not isinstance(travel, dict):
        return {'partner_id': partner.get('partner_id') if isinstance(partner, dict) else None, 'eta_minutes': None, 'eligible': False}

    leg1 = travel.get((partner.get('zone'), order.get('restaurant_id')))
    leg2 = travel.get((order.get('restaurant_id'), order.get('destination_zone')))
    workload = partner.get('workload_minutes', 0)
    prep = order.get('prep_minutes', 0)

    if not all(_is_non_neg_num(t) for t in (now, leg1, leg2, workload, prep)):
        return {'partner_id': partner.get('partner_id'), 'eta_minutes': None, 'eligible': False}

    pickup = now + leg1 + workload
    return {
        'partner_id': partner.get('partner_id'),
        'pickup_minutes': pickup,
        'eta_minutes': pickup + prep + leg2,
        'eligible': True
    }


def assign_order(order, partners, travel, now=0):
    if not isinstance(order, dict):
        return {'order_id': None, 'partner_id': None, 'eta_minutes': None, 'reason': 'invalid order'}

    order_id = order.get('order_id')
    restaurant_id = order.get('restaurant_id')
    destination_zone = order.get('destination_zone')
    prep_minutes = order.get('prep_minutes')

    if (
        not _is_non_empty_str(order_id)
        or not _is_non_empty_str(restaurant_id)
        or not _is_non_empty_str(destination_zone)
        or not _is_non_neg_num(prep_minutes)
        or not _is_non_neg_num(now)
    ):
        return {
            'order_id': order_id,
            'partner_id': None,
            'eta_minutes': None,
            'reason': 'invalid order or time data'
        }

    options = []
    for partner in partners:
        estimate = estimate_eta(order, partner, travel, now)
        if estimate['eligible']:
            options.append(estimate)

    if not options:
        return {'order_id': order_id, 'partner_id': None, 'eta_minutes': None, 'reason': 'no eligible partner or missing time data'}

    chosen = min(options, key=lambda item: (item['eta_minutes'], str(item['partner_id'])))
    return {
        'order_id': order_id,
        'partner_id': chosen['partner_id'],
        'pickup_minutes': chosen['pickup_minutes'],
        'eta_minutes': chosen['eta_minutes'],
        'reason': 'assigned'
    }


def process_cancellation(partner, order_id, event_id):
    out = deepcopy(partner)
    out.setdefault('active_order_ids', [])
    out.setdefault('processed_cancellation_ids', [])
    if order_id in out['active_order_ids']:
        out['active_order_ids'].remove(order_id)
        out['workload_minutes'] = max(0, out.get('workload_minutes', 0) - out.get('minutes_by_order', {}).get(order_id, 0))
    out['processed_cancellation_ids'].append(event_id)
    return out