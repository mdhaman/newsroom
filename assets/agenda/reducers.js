import {
    SET_EVENT_QUERY,
    RECIEVE_ITEMS,
    INIT_DATA,
    SELECT_DATE,
    WATCH_EVENTS,
    STOP_WATCHING_EVENTS,
    UPDATE_ITEMS,
} from './actions';

import { get, isEmpty } from 'lodash';
import { getActiveDate } from 'local-store';
import { EXTENDED_VIEW } from 'wire/defaults';
import { searchReducer } from 'search/reducers';
import { defaultReducer } from '../reducers';
import { EARLIEST_DATE } from './utils';
import moment from 'moment';

const initialState = {
    items: [],
    itemsById: {},
    aggregations: null,
    activeItem: null,
    previewItem: null,
    previewGroup: null,
    previewPlan: null,
    openItem: null,
    isLoading: false,
    resultsFiltered: false,
    totalItems: null,
    activeQuery: null,
    user: null,
    company: null,
    topics: [],
    selectedItems: [],
    bookmarks: false,
    context: null,
    formats: [],
    newItems: [],
    newItemsData: null,
    newItemsByTopic: {},
    readItems: {},
    agenda: {
        activeView: EXTENDED_VIEW,
        activeDate: Date.now(),
        activeGrouping: 'day',
    },
    search: searchReducer(),
    detail: false,
    userSections: {}
};

function recieveItems(state, data) {
    const itemsById = Object.assign({}, state.itemsById);
    const items = data._items.map((item) => {
        itemsById[item._id] = item;
        return item._id;
    });
    const createdFilter = get(state, 'search.createdFilter', {});

    let activeDate = state.agenda.activeDate || Date.now();
    if (state.bookmarks) {
        activeDate = EARLIEST_DATE;
    }
    if (!isEmpty(createdFilter.from) || !isEmpty(createdFilter.to)) {
        activeDate = moment().valueOf(); // default for 'now/d'
        if (createdFilter.from === 'now/d') {
            activeDate = moment().valueOf();
        } else if (createdFilter.from === 'now/w') {
            activeDate =  moment(activeDate).isoWeekday(1).valueOf();
        } else if (createdFilter.from === 'now/M') {
            activeDate =  moment(activeDate).startOf('month').valueOf();
        } else if (!isEmpty(createdFilter.from)) {
            activeDate = moment(createdFilter.from).valueOf();
        } else {
            activeDate = EARLIEST_DATE;
        }
    } else if (!state.bookmarks && activeDate === EARLIEST_DATE) {
        activeDate = getActiveDate() || moment().valueOf();
    }

    const agenda = {
        ...state.agenda,
        activeDate,
    };

    return {
        ...state,
        items,
        itemsById,
        isLoading: false,
        totalItems: data._meta.total,
        aggregations: data._aggregations || null,
        newItems: [],
        newItemsData: null,
        agenda,
    };
}


function _agendaReducer(state, action) {
    switch (action.type) {

    case SELECT_DATE:
        return {
            ...state,
            selectedItems: [],
            activeDate: action.dateString,
            activeGrouping: action.grouping || 'day',
        };

    default:
        return state;
    }
}

export default function agendaReducer(state = initialState, action) {
    switch (action.type) {

    case RECIEVE_ITEMS:
        return recieveItems(state, action.data);

    case SET_EVENT_QUERY:
        return {...state, query: action.query, activeItem: null};

    case WATCH_EVENTS: {
        const itemsById = Object.assign({}, state.itemsById);
        action.items.forEach((_id) => {
            const watches = get(itemsById[_id], 'watches', []).concat(state.user);
            itemsById[_id] = Object.assign({}, itemsById[_id], {watches});
        });

        return {...state, itemsById};
    }

    case STOP_WATCHING_EVENTS: {
        const itemsById = Object.assign({}, state.itemsById);
        action.items.forEach((_id) => {
            const watches = get(itemsById[_id], 'watches', []).filter((userId) => userId !== state.user);
            itemsById[_id] = Object.assign({}, itemsById[_id], {watches});
        });

        return {...state, itemsById};
    }

    case UPDATE_ITEMS: {
        const itemsById = Object.assign({}, state.itemsById);
        get(action.data, '_items', []).map(item => {
            if(itemsById[item._id]) {
                itemsById[item._id] = item;
            }
        });

        return {
            ...state,
            itemsById,
        };
    }

    case INIT_DATA: {
        const navigations = get(action, 'agendaData.navigations', []);
        const openItem = get(action, 'agendaData.item', null);
        const agenda = {
            ...state.agenda,
            activeDate: action.agendaData.bookmarks ? EARLIEST_DATE : action.activeDate || state.agenda.activeDate,
        };
        
        return {
            ...state,
            readItems: action.readData || {},
            user: action.agendaData.user || null,
            topics: action.agendaData.topics || [],
            company: action.agendaData.company || null,
            bookmarks: action.agendaData.bookmarks || false,
            formats: action.agendaData.formats || [],
            search: Object.assign({}, state.search, {navigations}),
            context: 'agenda',
            openItem: openItem,
            detail: !!openItem,
            agenda,
            savedItemsCount: action.agendaData.saved_items || null,
            userSections: action.agendaData.userSections || {}
        };
    }

    case SELECT_DATE:
        return {
            ...state,
            activeItem: null,
            previewItem: null,
            agenda: _agendaReducer(state.agenda, action)
        };

    default:
        return defaultReducer(state || initialState, action);
    }
}
