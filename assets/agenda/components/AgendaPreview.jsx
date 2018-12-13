import React from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import { get } from 'lodash';

import { isEqualItem } from 'wire/utils';
import PreviewActionButtons from 'components/PreviewActionButtons';

import Preview from 'ui/components/Preview';

import {
    hasCoverages,
    isCanceled,
    isPostponed,
    isRescheduled,
    getInternalNote,
    isCoverageForExtraDay,
    isCoverageOnPreviousDay,
} from '../utils';
import AgendaName from './AgendaName';
import AgendaTime from './AgendaTime';
import AgendaMeta from './AgendaMeta';
import AgendaEdNote from './AgendaEdNote';
import AgendaInternalNote from './AgendaInternalNote';
import AgendaPreviewCoverages from './AgendaPreviewCoverages';
import AgendaPreviewImage from './AgendaPreviewImage';
import AgendaLongDescription from './AgendaLongDescription';
import AgendaPreviewAttachments from './AgendaPreviewAttachments';
import AgendaCoverageRequest from './AgendaCoverageRequest';

class AgendaPreview extends React.PureComponent {
    constructor(props) {
        super(props);
    }

    componentDidUpdate(nextProps) {
        if (!isEqualItem(nextProps.item, this.props.item) && this.props.item) {
            this.preview.scrollTop = 0; // reset scroll on change
        }
    }

    render() {
        const {item, user, actions, openItemDetails, requestCoverage, previewGroup, previewPlan} = this.props;

        const isWatching = get(item, 'watches', []).includes(user);

        const previewClassName = classNames('wire-column__preview', {
            'wire-column__preview--covering': hasCoverages(item),
            'wire-column__preview--not-covering': !hasCoverages(item),
            'wire-column__preview--postponed': isPostponed(item),
            'wire-column__preview--canceled': isCanceled(item),
            'wire-column__preview--rescheduled': isRescheduled(item),
            'wire-column__preview--open': !!item,
            'wire-column__preview--watched': isWatching,
        });

        const currentCoverage = [];
        const previousCoverage = [];
        // get current and preview coverages
        get(item, 'coverages', [])
            .forEach((coverage) => {
                if (coverage.planning_id === get(previewPlan, '_id')) {
                    if (isCoverageForExtraDay(coverage, previewGroup)) {
                        currentCoverage.push(coverage);
                    } else if (isCoverageOnPreviousDay(coverage, previewGroup)) {
                        previousCoverage.push(coverage)
                    }
                }
            });

        return (
            <div className={previewClassName}>
                {item &&
                    <Preview onCloseClick={this.props.closePreview} published={item.versioncreated}>
                        <div className='wire-column__preview__top-bar'>
                            <PreviewActionButtons item={item} user={user} actions={actions} />
                        </div>

                        <div id='preview-article' className='wire-column__preview__content' ref={(preview) => this.preview = preview}>
                            <AgendaName item={item} />
                            <AgendaTime item={item} group={previewGroup} />
                            <AgendaPreviewImage item={item} onClick={openItemDetails} />
                            <AgendaMeta item={item} />
                            <AgendaLongDescription item={item} plan={previewPlan}/>
                            <AgendaPreviewCoverages item={item}
                                currentCoverage={currentCoverage}
                                previousCoverage={previousCoverage} />
                            <AgendaCoverageRequest item={item} requestCoverage={requestCoverage}/>
                            <AgendaPreviewAttachments item={item} />
                            <AgendaEdNote item={item} plan={previewPlan || {}}/>
                            <AgendaInternalNote internalNote={getInternalNote(item, previewPlan || {})} />
                        </div>
                    </Preview>
                }
            </div>
        );
    }
}

AgendaPreview.propTypes = {
    user: PropTypes.string,
    item: PropTypes.object,
    actions: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        action: PropTypes.func,
        url: PropTypes.func,
    })),
    followEvent: PropTypes.func,
    closePreview: PropTypes.func,
    openItemDetails: PropTypes.func,
    requestCoverage: PropTypes.func,
    previewGroup: PropTypes.string,
    previewPlan: PropTypes.object,
};

export default AgendaPreview;
