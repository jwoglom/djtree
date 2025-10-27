'use strict';
{
    const $ = django.jQuery;

    // Helper to fetch person display name
    async function fetchPersonName(personId) {
        try {
            const response = await $.ajax({
                url: `/api/people/${personId}/`,
                type: 'GET',
                dataType: 'json'
            });

            // Construct display name from API response
            if (response && response.name) {
                const { first_name, middle_name, last_name } = response.name;
                const parts = [first_name, middle_name, last_name].filter(p => p);
                return parts.join(' ') || `Person #${personId}`;
            }
            return `Person #${personId}`;
        } catch (error) {
            console.error('Error fetching person name:', error);
            return `Person #${personId}`;
        }
    }

    // Helper to prepopulate select field with initial value
    async function prepopulateField($element) {
        const initialValue = $element.val();

        if (initialValue && initialValue !== '') {
            console.log('Prepopulating field with initial value:', initialValue);

            // Check if option already has text
            const $option = $element.find('option:selected');
            if ($option.length && $option.text() && $option.text() !== initialValue) {
                // Option already has proper text, no need to fetch
                console.log('Option already has text:', $option.text());
                return;
            }

            // Fetch the display name
            const displayName = await fetchPersonName(initialValue);
            console.log('Fetched display name:', displayName);

            // Update or create the option
            if ($option.length) {
                $option.text(displayName);
            } else {
                const newOption = new Option(displayName, initialValue, true, true);
                $element.append(newOption);
            }
        }
    }

    // Parse URL parameters and add initial values to formsets
    async function handleUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const parentsParam = urlParams.get('parents');
        const childrenParam = urlParams.get('children');
        const spouseParam = urlParams.get('spouse');

        console.log('URL parameters - parents:', parentsParam, 'children:', childrenParam, 'spouse:', spouseParam);

        // Handle parents (formset prefix is "child_relationships")
        if (parentsParam) {
            const parentIds = parentsParam.split(',').map(id => id.trim()).filter(id => id);
            for (let index = 0; index < parentIds.length; index++) {
                const parentId = parentIds[index];
                const $field = $(`#id_child_relationships-${index}-parent`);
                if ($field.length && !$field.val()) {
                    console.log(`Setting parent field ${index} to ${parentId}`);

                    // Fetch the person name
                    const displayName = await fetchPersonName(parentId);
                    console.log(`Parent ${index} display name:`, displayName);

                    // Create option with both value and text
                    const option = new Option(displayName, parentId, true, true);
                    $field.append(option);
                }
            }
        }

        // Handle children (formset prefix is "parent_relationships")
        if (childrenParam) {
            const childIds = childrenParam.split(',').map(id => id.trim()).filter(id => id);
            for (let index = 0; index < childIds.length; index++) {
                const childId = childIds[index];
                const $field = $(`#id_parent_relationships-${index}-child`);
                if ($field.length && !$field.val()) {
                    console.log(`Setting child field ${index} to ${childId}`);

                    // Fetch the person name
                    const displayName = await fetchPersonName(childId);
                    console.log(`Child ${index} display name:`, displayName);

                    // Create option with both value and text
                    const option = new Option(displayName, childId, true, true);
                    $field.append(option);
                }
            }
        }

        // Handle spouse (formset prefix is "marriageevents")
        if (spouseParam) {
            const spouseId = spouseParam.trim();
            const $field = $('#id_marriageevents-0-other_person');
            if ($field.length && !$field.val()) {
                console.log(`Setting spouse field to ${spouseId}`);

                // Fetch the person name
                const displayName = await fetchPersonName(spouseId);
                console.log(`Spouse display name:`, displayName);

                // Create option with both value and text
                const option = new Option(displayName, spouseId, true, true);
                $field.append(option);
            }
        }
    }

    $.fn.djangoAdminSelect2 = function() {
        const $elements = this;

        // Process all elements sequentially
        (async function() {
            for (let i = 0; i < $elements.length; i++) {
                const element = $elements[i];
                const $element = $(element);

                console.log('Initializing Select2 on field:', element.id, 'current value:', $element.val());

                // Check if field has value but no option text (shouldn't happen with our new approach)
                const currentVal = $element.val();
                if (currentVal) {
                    const $option = $element.find('option:selected');
                    if ($option.length && $option.text() === currentVal) {
                        console.log('Field has value but no display text, fetching...');
                        await prepopulateField($element);
                    } else {
                        console.log('Field already has proper option:', $option.text());
                    }
                }

                // Initialize Select2
                $element.select2({
                    ajax: {
                        data: (params) => {
                            return {
                                term: params.term,
                                page: params.page,
                                app_label: element.dataset.appLabel,
                                model_name: element.dataset.modelName,
                                field_name: element.dataset.fieldName
                            };
                        }
                    }
                });
            }
        })();

        return this;
    };

    $(async function() {
        console.log('Page loaded, handling URL parameters...');

        // First, handle URL parameters to set field values (with person names)
        await handleUrlParameters();

        console.log('URL parameters handled, initializing Select2 widgets...');

        // Initialize Select2 on all autocomplete fields
        $('.admin-autocomplete').not('[name*=__prefix__]').djangoAdminSelect2();
    });

    document.addEventListener('formset:added', (event) => {
        $(event.target).find('.admin-autocomplete').djangoAdminSelect2();
    });
}
