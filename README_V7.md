# AMP TRADE FIND – Backend V7

V7 adds an Android-ready signal contract.

## Dashboard
GET /api/v1/dashboard

Now includes:
- signal_id
- score components
- trade_plan
- notification object
- 20 recent paper signals

## Signal detail
GET /api/v1/signals/{signal_id}

Returns:
- stored signal
- stored market snapshot
- entry / SL / TP1 / TP2
- outcome
- MFE / MAE prices
- strategy version

## Notification object

The backend generates a stable payload with:
- title
- body
- direction
- signal ID
- scores
- trade plan
- dedupe key
- deep link

In V7:
- foreground local notification may be shown for a paper candidate
- server push remains disabled
- should_notify_push is always false
- push blocker is PAPER_MODE_VALIDATION_REQUIRED

This is deliberate.
