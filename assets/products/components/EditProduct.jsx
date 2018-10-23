import React from 'react';
import PropTypes from 'prop-types';
import TextInput from 'components/TextInput';
import CheckboxInput from 'components/CheckboxInput';
import {get} from 'lodash';

import { gettext, getProductQuery } from 'utils';
import EditPanel from '../../components/EditPanel';
import {sectionsPropType} from '../../features/sections/types';
import {isProducts, getFilterType} from '../util';

class EditProduct extends React.Component {
    constructor(props) {
        super(props);
        this.handleTabClick = this.handleTabClick.bind(this);
        this.getProductTestButton = this.getProductTestButton.bind(this);
        this.state = {
            activeTab: 'product-details',
            activeProduct: props.product._id,
        };

        const productTabLabel = isProducts(this.props.settingsContext) ? gettext('Product') : gettext('Section Filter');
        this.tabs = [
            {label: productTabLabel, name: 'product-details', condition: (ctx) => true},
            {label: gettext('Companies'), name: 'companies', condition: isProducts},
            {label: gettext('Navigation'), name: 'navigations', condition: isProducts}
        ];
    }

    handleTabClick(event) {
        this.setState({activeTab: event.target.name});
        if(event.target.name === 'companies') {
            this.props.fetchCompanies();
        }
        if(event.target.name === 'navigations') {
            this.props.fetchNavigations();
        }
    }

    getProductTestButton(product) {
        const q = getProductQuery(product);
        const filterType =  getFilterType(this.props.settingsContext);

        if (q) {
            return (
                <a href={`/wire?q=${q}`} target="_blank"
                    className='btn btn-outline-secondary float-right'>
                    {gettext('Test {{filterType}}', {filterType:filterType})}
                </a>
            );
        }
    }

    render() {
        return (
            <div className='list-item__preview'>
                <div className='list-item__preview-header'>
                    <h3>{this.props.product.name}</h3>
                    <button
                        id='hide-sidebar'
                        type='button'
                        className='icon-button'
                        data-dismiss='modal'
                        aria-label='Close'
                        onClick={this.props.onClose}>
                        <i className="icon--close-thin icon--gray" aria-hidden='true'></i>
                    </button>
                </div>

                <ul className='nav nav-tabs'>
                    {this.tabs.map((tab) => tab.condition(this.props.settingsContext) && (
                        <li key={tab.name} className='nav-item'>
                            <a
                                name={tab.name}
                                className={`nav-link ${this.state.activeTab === tab.name && 'active'}`}
                                href='#'
                                onClick={this.handleTabClick}>{tab.label}
                            </a>
                        </li>
                    ))}
                </ul>

                <div className='tab-content'>
                    {this.state.activeTab === 'product-details' &&
                        <div className='tab-pane active' id='product-details'>
                            <form>
                                <div className="list-item__preview-form">
                                    <TextInput
                                        name='name'
                                        label={gettext('Name')}
                                        value={this.props.product.name}
                                        onChange={this.props.onChange}
                                        error={this.props.errors ? this.props.errors.name : null}/>

                                    <TextInput
                                        name='description'
                                        label={gettext('Description')}
                                        value={this.props.product.description}
                                        onChange={this.props.onChange}
                                        error={this.props.errors ? this.props.errors.description : null}/>

                                    <div className="form-group">
                                        <label htmlFor="sd_product_id">{gettext('Superdesk Product Id')}</label>
                                        <input className="form-control"
                                            id="sd_product_id"
                                            name="sd_product_id"
                                            value={this.props.product.sd_product_id || ''}
                                            onChange={this.props.onChange}
                                        />
                                        {this.props.product.sd_product_id &&
                                        <a href={`/${this.props.product.product_type || 'wire'}?q=products.code:${this.props.product.sd_product_id}`} target="_blank"
                                            className='btn btn-outline-secondary float-right mt-2'>{gettext('Test product id')}
                                        </a>}
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="query">{gettext('Query')}</label>
                                        <textarea className="form-control"
                                            id="query"
                                            name="query"
                                            value={this.props.product.query || ''}
                                            onChange={this.props.onChange}
                                        />
                                        {this.props.product.query &&
                                        <a href={`/${this.props.product.product_type || 'wire'}?q=${this.props.product.query}`} target="_blank"
                                            className='btn btn-outline-secondary float-right mt-3'>{gettext('Test query')}
                                        </a>}
                                    </div>

                                    <CheckboxInput
                                        name='is_enabled'
                                        label={gettext('Enabled')}
                                        value={this.props.product.is_enabled}
                                        onChange={this.props.onChange}/>
                                </div>
                                <div className='list-item__preview-footer'>
                                    {this.getProductTestButton(this.props.product)}
                                    <input
                                        type='button'
                                        className='btn btn-outline-primary'
                                        value={gettext('Save')}
                                        onClick={this.props.onSave}/>
                                    <input
                                        type='button'
                                        className='btn btn-outline-secondary'
                                        value={gettext('Delete')}
                                        onClick={this.props.onDelete}/>
                                </div>
                            </form>
                        </div>
                    }
                    {this.state.activeTab === 'companies' &&
                        <EditPanel
                            parent={this.props.product}
                            items={this.props.companies}
                            field="companies"
                            onSave={this.props.saveCompanies}
                        />
                    }
                    {this.state.activeTab === 'navigations' &&
                        <EditPanel
                            parent={this.props.product}
                            items={this.props.navigations}
                            field="navigations"
                            onSave={this.props.saveNavigations}
                            groups={this.props.sections}
                            groupField={'product_type'}
                            groupDefaultValue={'wire'}
                        />
                    }
                </div>
            </div>
        );
    }
}

EditProduct.propTypes = {
    product: PropTypes.object.isRequired,
    onChange: PropTypes.func,
    errors: PropTypes.object,
    companies: PropTypes.arrayOf(PropTypes.object),
    navigations: PropTypes.arrayOf(PropTypes.object),
    onSave: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
    onDelete: PropTypes.func.isRequired,
    saveCompanies: PropTypes.func.isRequired,
    saveNavigations: PropTypes.func.isRequired,
    fetchCompanies: PropTypes.func.isRequired,
    fetchNavigations: PropTypes.func.isRequired,
    products: PropTypes.arrayOf(PropTypes.object),
    sections: sectionsPropType,
    settingsContext: PropTypes.string.isRequired
};

export default EditProduct;
