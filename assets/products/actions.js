import { gettext, notify, errorHandler } from 'utils';
import server from 'server';
import { initSections } from 'features/sections/actions';
import { getActionMessage, isSectionFilters, isProducts} from './util';


export const SELECT_PRODUCT = 'SELECT_PRODUCT';
export function selectProduct(id) {
    return {type: SELECT_PRODUCT, id};
}

export const EDIT_PRODUCT = 'EDIT_PRODUCT';
export function editProduct(event) {
    return {type: EDIT_PRODUCT, event};
}

export const NEW_PRODUCT = 'NEW_PRODUCT';
export function newProduct() {
    return {type: NEW_PRODUCT};
}

export const CANCEL_EDIT = 'CANCEL_EDIT';
export function cancelEdit(event) {
    return {type: CANCEL_EDIT, event};
}

export const SET_QUERY = 'SET_QUERY';
export function setQuery(query) {
    return {type: SET_QUERY, query};
}

export const QUERY_PRODUCTS = 'QUERY_PRODUCTS';
export function queryProducts() {
    return {type: QUERY_PRODUCTS};
}

export const GET_PRODUCTS = 'GET_PRODUCTS';
export function getProducts(data) {
    return {type: GET_PRODUCTS, data};
}

export const GET_COMPANIES = 'GET_COMPANIES';
export function getCompanies(data) {
    return {type: GET_COMPANIES, data};
}

export const GET_NAVIGATIONS = 'GET_NAVIGATIONS';
export function getNavigations(data) {
    return {type: GET_NAVIGATIONS, data};
}

export const UPDATE_PRODUCT_COMPANIES = 'UPDATE_PRODUCT_COMPANIES';
export function updateProductCompanies(product, companies) {
    return {type: UPDATE_PRODUCT_COMPANIES, product, companies};
}

export const UPDATE_PRODUCT_NAVIGATIONS = 'UPDATE_PRODUCT_NAVIGATIONS';
export function updateProductNavigations(product, navigations) {
    return {type: UPDATE_PRODUCT_NAVIGATIONS, product, navigations};
}

export const SET_ERROR = 'SET_ERROR';
export function setError(errors) {
    return {type: SET_ERROR, errors};
}

export const SET_PRODUCTS_SETTINGS_CONTEXT = 'SET_PRODUCTS_SETTINGS_CONTEXT';
export function setProductsSettingsContext(data) {
    return {type: SET_PRODUCTS_SETTINGS_CONTEXT, data};
}

/**
 * Fetches products
 *
 */
export function fetchProducts() {
    return function (dispatch, getState) {
        dispatch(queryProducts());
        const query = getState().query || '';
        const isSectionFilter = isSectionFilters(getState().productSettingsContext);


        return server.get(`/products/search?q=${query}&where={"is_section_filter":${isSectionFilter}}`)
            .then((data) => dispatch(getProducts(data)))
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}


/**
 * Creates new products
 *
 */
export function postProduct() {
    return function (dispatch, getState) {

        const product = getState().productToEdit;
        const url = `/products/${product._id ? product._id : 'new'}`;
        const context = getState().productSettingsContext;

        return server.post(url, product)
            .then(function() {
                if (product._id) {
                    notify.success(getActionMessage(context, gettext('updated')));
                } else {
                    notify.success(getActionMessage(context, gettext('created')));
                }
                dispatch(fetchProducts());
            })
            .catch((error) => errorHandler(error, dispatch, setError));

    };
}


/**
 * Deletes a product
 *
 */
export function deleteProduct() {
    return function (dispatch, getState) {

        const product = getState().productToEdit;
        const url = `/products/${product._id}`;
        const context = getState().productSettingsContext;

        return server.del(url)
            .then(() => {
                notify.success(getActionMessage(context, gettext('deleted')));
                dispatch(fetchProducts());
            })
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}


/**
 * Fetches companies
 *
 */
export function fetchCompanies() {
    return function (dispatch) {
        return server.get('/companies/search')
            .then((data) => {
                dispatch(getCompanies(data));
            })
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}

/**
 * Saves companies for a product
 *
 */
export function saveCompanies(companies) {
    return function (dispatch, getState) {
        const product = getState().productToEdit;
        const context = getState().productSettingsContext;

        return server.post(`/products/${product._id}/companies`, {companies})
            .then(() => {
                notify.success(getActionMessage(context, gettext('updated')));
                dispatch(updateProductCompanies(product, companies));
            })
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}

/**
 * Fetches navigations
 *
 */
export function fetchNavigations() {
    return function (dispatch) {
        return server.get('/navigations/search')
            .then((data) => {
                dispatch(getNavigations(data));
            })
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}

/**
 * Saves navigations for a product
 *
 */
export function saveNavigations(navigations) {
    return function (dispatch, getState) {
        const product = getState().productToEdit;
        const context = getState().productSettingsContext;
        return server.post(`/products/${product._id}/navigations`, {navigations})
            .then(() => {
                notify.success(getActionMessage(context, gettext('updated')));
                dispatch(updateProductNavigations(product, navigations));
            })
            .catch((error) => errorHandler(error, dispatch, setError));
    };
}

export function initViewData(data) {
    return function (dispatch) {
        dispatch(getProducts(data.products));
        dispatch(getCompanies(data.companies));
        dispatch(getNavigations(data.navigations));
        dispatch(initSections(data.sections));
        dispatch(setProductsSettingsContext(data.settings_context));
    };
}
