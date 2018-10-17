import { gettext } from 'utils';

export const isProducts = (context) => context === 'products';
export const isSectionFilters = (context) => context === 'section_filters';
export const getFilterType = (context) => isProducts(context) ? gettext('Product') : gettext('Section Filter');

export const getActionMessage = (context, action) => {
    const filterType = getFilterType(context);

    return gettext('{{filterType}} {{action}} successfully', {filterType: filterType, action: action});
};