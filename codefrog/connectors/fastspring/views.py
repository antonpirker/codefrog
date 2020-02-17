import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from core import fastspring

logger = logging.getLogger(__name__)


@csrf_exempt
def payment(request):
    logger.debug('########## payment')
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.headers: %s ' % request.headers)
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.body: %s' % request.body)
    logger.debug('-----------------------------------------------------------')

    request_signature = request.headers['X-Fs-Signature'] if 'X-Fs-Signature' in request.headers else None
    # TODO: remove test data
    test_headers = {'Content-Length': '17054', 'Content-Type': 'application/json; charset=UTF-8', 'X-Forwarded-For': '::ffff:107.23.30.83', 'X-Forwarded-Proto': 'http', 'X-Pagekite-Port': '80', 'X-Fs-Signature': 'eOHZNyGvf95/ZkxjIwg1ePDvoRZIcVtDmuEZn0uimvw=', 'User-Agent': 'FS', 'Host': 'antonpirker.pagekite.me'}
    request_signature = test_headers['X-Fs-Signature']

    # TODO: implement security check
    #    hmac_sha256_key = 'test_not_so_important_what_the_secret_key_is_but_it_should_be_fairly_long_:-)'
    #    my_signature = ''
    #    if my_signature == request.headers['X-Fs-Signature']:
    #        payload = json.loads()

    payload = json.loads(request.body) if request.body and request.body != b'' else None
    # TODO: remove test data
    test_body = '{"events":[{"id":"OwjeRk7-R8-leXkI6K8XOw","processed":false,"created":1580748797536,"type":"subscription.activated","live":false,"data":{"id":"81QWuXvsTnGG5TvSQ0CM-A","subscription":"81QWuXvsTnGG5TvSQ0CM-A","active":true,"state":"active","changed":1580748797420,"changedValue":1580748797420,"changedInSeconds":1580748797,"changedDisplay":"03/02/2020","live":false,"currency":"EUR","account":{"id":"owAaQjKPRXaG6ecKk1KWkQ","account":"owAaQjKPRXaG6ecKk1KWkQ","contact":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"language":"en","country":"AT","lookup":{"global":"w1EZsDOsSoiRD-QQqTOm5A"},"url":"https://codefrog.test.onfastspring.com/account"},"product":{"product":"team-plan-billed-monthly","parent":null,"display":{"en":"Team plan billed monthly"},"description":{},"image":"https://d8y8nchqlnmka.cloudfront.net/r9h9vAbXR0s/vDa7d0SDQ2M/frog-black-no-background.png","fulfillments":{},"format":"saas","pricing":{"interval":"month","intervalLength":1,"intervalCount":null,"quantityBehavior":"allow","quantityDefault":1,"price":{"USD":25.0},"dateLimitsEnabled":false,"reminderNotification":{"enabled":true,"interval":"week","intervalLength":1},"overdueNotification":{"enabled":true,"interval":"week","intervalLength":1,"amount":4},"cancellation":{"interval":"week","intervalLength":1}}},"sku":null,"display":"Team plan billed monthly","quantity":1,"adhoc":false,"autoRenew":true,"price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","next":1583193600000,"nextValue":1583193600000,"nextInSeconds":1583193600,"nextDisplay":"03/03/2020","end":null,"endValue":null,"endInSeconds":null,"endDisplay":null,"canceledDate":null,"canceledDateValue":null,"canceledDateInSeconds":null,"canceledDateDisplay":null,"deactivationDate":null,"deactivationDateValue":null,"deactivationDateInSeconds":null,"deactivationDateDisplay":null,"sequence":1,"periods":null,"remainingPeriods":null,"begin":1580688000000,"beginValue":1580688000000,"beginInSeconds":1580688000,"beginDisplay":"03/02/2020","intervalUnit":"month","intervalLength":1,"nextChargeCurrency":"EUR","nextChargeDate":1583193600000,"nextChargeDateValue":1583193600000,"nextChargeDateInSeconds":1583193600,"nextChargeDateDisplay":"03/03/2020","nextChargePreTax":23.33,"nextChargePreTaxDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargePreTaxInPayoutCurrency":24.99,"nextChargePreTaxInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextChargeTotal":23.33,"nextChargeTotalDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargeTotalInPayoutCurrency":24.99,"nextChargeTotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextNotificationType":"PAYMENT_REMINDER","nextNotificationDate":1582588800000,"nextNotificationDateValue":1582588800000,"nextNotificationDateInSeconds":1582588800,"nextNotificationDateDisplay":"25/02/2020","paymentReminder":{"intervalUnit":"week","intervalLength":1},"paymentOverdue":{"intervalUnit":"week","intervalLength":1,"total":4,"sent":0},"cancellationSetting":{"cancellation":"AFTER_LAST_NOTIFICATION","intervalUnit":"week","intervalLength":1},"instructions":[{"product":"team-plan-billed-monthly","type":"regular","periodStartDate":null,"periodStartDateValue":null,"periodStartDateInSeconds":null,"periodStartDateDisplay":null,"periodEndDate":null,"periodEndDateValue":null,"periodEndDateInSeconds":null,"periodEndDateDisplay":null,"intervalUnit":"month","intervalLength":1,"discountPercent":0,"discountPercentValue":0,"discountPercentDisplay":"0\xc2\xa0%","discountTotal":0.0,"discountTotalDisplay":"\xe2\x82\xac\xc2\xa00,00","discountTotalInPayoutCurrency":0.0,"discountTotalInPayoutCurrencyDisplay":"US$\xc2\xa00,00","unitDiscount":0.0,"unitDiscountDisplay":"\xe2\x82\xac\xc2\xa00,00","unitDiscountInPayoutCurrency":0.0,"unitDiscountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","priceTotal":28.0,"priceTotalDisplay":"\xe2\x82\xac\xc2\xa028,00","priceTotalInPayoutCurrency":29.99,"priceTotalInPayoutCurrencyDisplay":"US$\xc2\xa029,99","unitPrice":28.0,"unitPriceDisplay":"\xe2\x82\xac\xc2\xa028,00","unitPriceInPayoutCurrency":29.99,"unitPriceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","total":28.0,"totalDisplay":"\xe2\x82\xac\xc2\xa028,00","totalInPayoutCurrency":29.99,"totalInPayoutCurrencyDisplay":"US$\xc2\xa029,99"}]}},{"id":"T5LnqDA_QGuOo4GNDzCH9A","processed":false,"created":1580748797661,"type":"payoutEntry.created","live":false,"data":{"orderId":"8xPG4V_cQD6NEJNHCXUzfw","reference":"CODEFROGIO200203-7104-54211","live":false,"order":{"order":"8xPG4V_cQD6NEJNHCXUzfw","id":"8xPG4V_cQD6NEJNHCXUzfw","reference":"CODEFROGIO200203-7104-54211","buyerReference":null,"ipAddress":"80.110.40.73","completed":true,"changed":1580748797620,"changedValue":1580748797620,"changedInSeconds":1580748797,"changedDisplay":"03/02/2020","language":"en","live":false,"currency":"EUR","payoutCurrency":"USD","invoiceUrl":"https://codefrog.test.onfastspring.com/account/order/CODEFROGIO200203-7104-54211/invoice","account":"owAaQjKPRXaG6ecKk1KWkQ","total":28.0,"totalDisplay":"\xe2\x82\xac\xc2\xa028,00","totalInPayoutCurrency":29.99,"totalInPayoutCurrencyDisplay":"US$\xc2\xa029,99","tax":4.67,"taxDisplay":"\xe2\x82\xac\xc2\xa04,67","taxInPayoutCurrency":5.0,"taxInPayoutCurrencyDisplay":"US$\xc2\xa05,00","subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","discountWithTax":0.0,"discountWithTaxDisplay":"\xe2\x82\xac\xc2\xa00,00","discountWithTaxInPayoutCurrency":0.0,"discountWithTaxInPayoutCurrencyDisplay":"US$\xc2\xa00,00","billDescriptor":"FS* fsprg.com","payment":{"type":"test","cardEnding":"4242"},"customer":{"first":"Marion","last":"Hallaba xxx","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"address":{"country":"AT","display":"AT"},"recipients":[{"recipient":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123","account":"owAaQjKPRXaG6ecKk1KWkQ","address":{"country":"AT","display":"AT"}}}],"notes":[],"items":[{"product":"team-plan-billed-monthly","quantity":1,"display":"Team plan billed monthly","sku":null,"subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","subscription":"81QWuXvsTnGG5TvSQ0CM-A","fulfillments":{},"driver":{"type":"cross-sell","path":"codefrog-popup-codefrog"}}]},"account":{"id":"owAaQjKPRXaG6ecKk1KWkQ","account":"owAaQjKPRXaG6ecKk1KWkQ","contact":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"language":"en","country":"AT","lookup":{"global":"w1EZsDOsSoiRD-QQqTOm5A"},"url":"https://codefrog.test.onfastspring.com/account"},"subscriptions":[{"id":"81QWuXvsTnGG5TvSQ0CM-A","subscription":"81QWuXvsTnGG5TvSQ0CM-A","active":true,"state":"active","changed":1580748797420,"changedValue":1580748797420,"changedInSeconds":1580748797,"changedDisplay":"03/02/2020","live":false,"currency":"EUR","account":"owAaQjKPRXaG6ecKk1KWkQ","product":"team-plan-billed-monthly","sku":null,"display":"Team plan billed monthly","quantity":1,"adhoc":false,"autoRenew":true,"price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","next":1583193600000,"nextValue":1583193600000,"nextInSeconds":1583193600,"nextDisplay":"03/03/2020","end":null,"endValue":null,"endInSeconds":null,"endDisplay":null,"canceledDate":null,"canceledDateValue":null,"canceledDateInSeconds":null,"canceledDateDisplay":null,"deactivationDate":null,"deactivationDateValue":null,"deactivationDateInSeconds":null,"deactivationDateDisplay":null,"sequence":1,"periods":null,"remainingPeriods":null,"begin":1580688000000,"beginValue":1580688000000,"beginInSeconds":1580688000,"beginDisplay":"03/02/2020","intervalUnit":"month","intervalLength":1,"nextChargeCurrency":"EUR","nextChargeDate":1583193600000,"nextChargeDateValue":1583193600000,"nextChargeDateInSeconds":1583193600,"nextChargeDateDisplay":"03/03/2020","nextChargePreTax":23.33,"nextChargePreTaxDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargePreTaxInPayoutCurrency":24.99,"nextChargePreTaxInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextChargeTotal":23.33,"nextChargeTotalDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargeTotalInPayoutCurrency":24.99,"nextChargeTotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextNotificationType":"PAYMENT_REMINDER","nextNotificationDate":1582588800000,"nextNotificationDateValue":1582588800000,"nextNotificationDateInSeconds":1582588800,"nextNotificationDateDisplay":"25/02/2020","paymentReminder":{"intervalUnit":"week","intervalLength":1},"paymentOverdue":{"intervalUnit":"week","intervalLength":1,"total":4,"sent":0},"cancellationSetting":{"cancellation":"AFTER_LAST_NOTIFICATION","intervalUnit":"week","intervalLength":1},"instructions":[{"product":"team-plan-billed-monthly","type":"regular","periodStartDate":null,"periodStartDateValue":null,"periodStartDateInSeconds":null,"periodStartDateDisplay":null,"periodEndDate":null,"periodEndDateValue":null,"periodEndDateInSeconds":null,"periodEndDateDisplay":null,"intervalUnit":"month","intervalLength":1,"discountPercent":0,"discountPercentValue":0,"discountPercentDisplay":"0\xc2\xa0%","discountTotal":0.0,"discountTotalDisplay":"\xe2\x82\xac\xc2\xa00,00","discountTotalInPayoutCurrency":0.0,"discountTotalInPayoutCurrencyDisplay":"US$\xc2\xa00,00","unitDiscount":0.0,"unitDiscountDisplay":"\xe2\x82\xac\xc2\xa00,00","unitDiscountInPayoutCurrency":0.0,"unitDiscountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","priceTotal":28.0,"priceTotalDisplay":"\xe2\x82\xac\xc2\xa028,00","priceTotalInPayoutCurrency":29.99,"priceTotalInPayoutCurrencyDisplay":"US$\xc2\xa029,99","unitPrice":28.0,"unitPriceDisplay":"\xe2\x82\xac\xc2\xa028,00","unitPriceInPayoutCurrency":29.99,"unitPriceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","total":28.0,"totalDisplay":"\xe2\x82\xac\xc2\xa028,00","totalInPayoutCurrency":29.99,"totalInPayoutCurrencyDisplay":"US$\xc2\xa029,99"}]}],"subtractions":{"tax":{"currency":"USD","amount":5.0,"percentage":0},"fastspring":{"currency":"USD","amount":2.7194,"percentage":10.8800}},"payouts":[{"payee":"codefrogio","currency":"USD","payout":"22.27","subtotal":22.27,"total":"29.99"}]}},{"id":"JHKUhY8VR6mkw21P7eO7Pw","processed":false,"created":1580748797636,"type":"order.completed","live":false,"data":{"order":"8xPG4V_cQD6NEJNHCXUzfw","id":"8xPG4V_cQD6NEJNHCXUzfw","reference":"CODEFROGIO200203-7104-54211","buyerReference":null,"ipAddress":"80.110.40.73","completed":true,"changed":1580748797620,"changedValue":1580748797620,"changedInSeconds":1580748797,"changedDisplay":"03/02/2020","language":"en","live":false,"currency":"EUR","payoutCurrency":"USD","invoiceUrl":"https://codefrog.test.onfastspring.com/account/order/CODEFROGIO200203-7104-54211/invoice","account":{"id":"owAaQjKPRXaG6ecKk1KWkQ","account":"owAaQjKPRXaG6ecKk1KWkQ","contact":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"language":"en","country":"AT","lookup":{"global":"w1EZsDOsSoiRD-QQqTOm5A"},"url":"https://codefrog.test.onfastspring.com/account"},"total":28.0,"totalDisplay":"\xe2\x82\xac\xc2\xa028,00","totalInPayoutCurrency":29.99,"totalInPayoutCurrencyDisplay":"US$\xc2\xa029,99","tax":4.67,"taxDisplay":"\xe2\x82\xac\xc2\xa04,67","taxInPayoutCurrency":5.0,"taxInPayoutCurrencyDisplay":"US$\xc2\xa05,00","subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","discountWithTax":0.0,"discountWithTaxDisplay":"\xe2\x82\xac\xc2\xa00,00","discountWithTaxInPayoutCurrency":0.0,"discountWithTaxInPayoutCurrencyDisplay":"US$\xc2\xa00,00","billDescriptor":"FS* fsprg.com","payment":{"type":"test","cardEnding":"4242"},"customer":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"address":{"country":"AT","display":"AT"},"recipients":[{"recipient":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123","account":{"id":"owAaQjKPRXaG6ecKk1KWkQ","account":"owAaQjKPRXaG6ecKk1KWkQ","contact":{"first":"MarioN","last":"Hallaba XXX","email":"maria@mailinator.com","company":"tst","phone":"+43123123123"},"language":"en","country":"AT","lookup":{"global":"w1EZsDOsSoiRD-QQqTOm5A"},"url":"https://codefrog.test.onfastspring.com/account"},"address":{"country":"AT","display":"AT"}}}],"notes":[],"items":[{"product":"team-plan-billed-monthly","quantity":1,"display":"Team plan billed monthly","sku":null,"subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","subscription":{"id":"81QWuXvsTnGG5TvSQ0CM-A","subscription":"81QWuXvsTnGG5TvSQ0CM-A","active":true,"state":"active","changed":1580748797420,"changedValue":1580748797420,"changedInSeconds":1580748797,"changedDisplay":"03/02/2020","live":false,"currency":"EUR","account":"owAaQjKPRXaG6ecKk1KWkQ","product":"team-plan-billed-monthly","sku":null,"display":"Team plan billed monthly","quantity":1,"adhoc":false,"autoRenew":true,"price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","discount":0.0,"discountDisplay":"\xe2\x82\xac\xc2\xa00,00","discountInPayoutCurrency":0.0,"discountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","subtotal":23.33,"subtotalDisplay":"\xe2\x82\xac\xc2\xa023,33","subtotalInPayoutCurrency":24.99,"subtotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","next":1583193600000,"nextValue":1583193600000,"nextInSeconds":1583193600,"nextDisplay":"03/03/2020","end":null,"endValue":null,"endInSeconds":null,"endDisplay":null,"canceledDate":null,"canceledDateValue":null,"canceledDateInSeconds":null,"canceledDateDisplay":null,"deactivationDate":null,"deactivationDateValue":null,"deactivationDateInSeconds":null,"deactivationDateDisplay":null,"sequence":1,"periods":null,"remainingPeriods":null,"begin":1580688000000,"beginValue":1580688000000,"beginInSeconds":1580688000,"beginDisplay":"03/02/2020","intervalUnit":"month","intervalLength":1,"nextChargeCurrency":"EUR","nextChargeDate":1583193600000,"nextChargeDateValue":1583193600000,"nextChargeDateInSeconds":1583193600,"nextChargeDateDisplay":"03/03/2020","nextChargePreTax":23.33,"nextChargePreTaxDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargePreTaxInPayoutCurrency":24.99,"nextChargePreTaxInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextChargeTotal":23.33,"nextChargeTotalDisplay":"\xe2\x82\xac\xc2\xa023,33","nextChargeTotalInPayoutCurrency":24.99,"nextChargeTotalInPayoutCurrencyDisplay":"US$\xc2\xa024,99","nextNotificationType":"PAYMENT_REMINDER","nextNotificationDate":1582588800000,"nextNotificationDateValue":1582588800000,"nextNotificationDateInSeconds":1582588800,"nextNotificationDateDisplay":"25/02/2020","paymentReminder":{"intervalUnit":"week","intervalLength":1},"paymentOverdue":{"intervalUnit":"week","intervalLength":1,"total":4,"sent":0},"cancellationSetting":{"cancellation":"AFTER_LAST_NOTIFICATION","intervalUnit":"week","intervalLength":1},"instructions":[{"product":"team-plan-billed-monthly","type":"regular","periodStartDate":null,"periodStartDateValue":null,"periodStartDateInSeconds":null,"periodStartDateDisplay":null,"periodEndDate":null,"periodEndDateValue":null,"periodEndDateInSeconds":null,"periodEndDateDisplay":null,"intervalUnit":"month","intervalLength":1,"discountPercent":0,"discountPercentValue":0,"discountPercentDisplay":"0\xc2\xa0%","discountTotal":0.0,"discountTotalDisplay":"\xe2\x82\xac\xc2\xa00,00","discountTotalInPayoutCurrency":0.0,"discountTotalInPayoutCurrencyDisplay":"US$\xc2\xa00,00","unitDiscount":0.0,"unitDiscountDisplay":"\xe2\x82\xac\xc2\xa00,00","unitDiscountInPayoutCurrency":0.0,"unitDiscountInPayoutCurrencyDisplay":"US$\xc2\xa00,00","price":28.0,"priceDisplay":"\xe2\x82\xac\xc2\xa028,00","priceInPayoutCurrency":29.99,"priceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","priceTotal":28.0,"priceTotalDisplay":"\xe2\x82\xac\xc2\xa028,00","priceTotalInPayoutCurrency":29.99,"priceTotalInPayoutCurrencyDisplay":"US$\xc2\xa029,99","unitPrice":28.0,"unitPriceDisplay":"\xe2\x82\xac\xc2\xa028,00","unitPriceInPayoutCurrency":29.99,"unitPriceInPayoutCurrencyDisplay":"US$\xc2\xa029,99","total":28.0,"totalDisplay":"\xe2\x82\xac\xc2\xa028,00","totalInPayoutCurrency":29.99,"totalInPayoutCurrencyDisplay":"US$\xc2\xa029,99"}]},"fulfillments":{},"driver":{"type":"cross-sell","path":"codefrog-popup-codefrog"}}]}}]}'
    payload = json.loads(test_body)

    for event in payload['events']:
        handlers = {
            'subscription.activated': fastspring.subscription_activated,
            'subscription.updated': fastspring.subscription_updated,
            'subscription.deactivated': fastspring.subscription_deactivated,
        }
        try:
            event_type = event['type']
            handlers[event_type](event)
        except KeyError:
            logger.info('Received unhandled web hook "%s"', event_type)

    return HttpResponse()