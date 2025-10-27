/*global opener */
'use strict';
{
    const initData = JSON.parse(document.getElementById('django-admin-popup-response-constants').dataset.popupResponse);

    // Check if we're in an iframe without window.opener
    const isIframe = window.parent !== window && !window.opener;

    if (isIframe) {
        // We're in an iframe, send message to parent to close
        console.log('In iframe, sending close message to parent');
        window.parent.postMessage({ action: 'dismissPopup', data: initData }, '*');
    } else if (window.opener) {
        // Original Django admin popup behavior
        switch (initData.action) {
            case 'change':
                opener.dismissChangeRelatedObjectPopup(window, initData.value, initData.obj, initData.new_value);
                break;
            case 'delete':
                opener.dismissDeleteRelatedObjectPopup(window, initData.value);
                break;
            default:
                opener.dismissAddRelatedObjectPopup(window, initData.value, initData.obj);
                break;
        }
        window.close();
    } else {
        // Fallback: close the window
        console.warn('No window.opener and not in iframe, closing window');
        window.close();
    }
}
