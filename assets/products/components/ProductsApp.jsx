import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import {
    newProduct,
    setQuery,
    fetchProducts,
} from '../actions';
import Products from './Products';
import ListBar from 'components/ListBar';
import { gettext } from 'utils';

import SectionSwitch from 'features/sections/SectionSwitch';
import { sectionsPropType } from 'features/sections/types';
import {getFilterType} from '../util';

class ProductsApp extends React.Component {
    constructor(props, context) {
        super(props, context);
    }

    render() {
        const filterType = getFilterType(this.props.settingsContext);

        return [
            <ListBar key="bar"
                onNewItem={this.props.newProduct}
                setQuery={this.props.setQuery}
                fetch={this.props.fetchProducts}
                buttonName={filterType}
            >
                <SectionSwitch
                    sections={this.props.sections}
                    activeSection={this.props.activeSection}
                />
            </ListBar>,
            <Products key="products" activeSection={this.props.activeSection} sections={this.props.sections} />
        ];
    }
}

ProductsApp.propTypes = {
    sections: sectionsPropType,
    activeSection: PropTypes.string.isRequired,

    fetchProducts: PropTypes.func,
    setQuery: PropTypes.func,
    newProduct: PropTypes.func,
    settingsContext: PropTypes.string.isRequired
};

const mapStateToProps = (state) => ({
    sections: state.sections.list,
    activeSection: state.sections.active,
    settingsContext: state.productSettingsContext,
});

const mapDispatchToProps = {
    fetchProducts,
    setQuery,
    newProduct,
};

export default connect(mapStateToProps, mapDispatchToProps)(ProductsApp);
