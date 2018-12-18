import React, {Fragment} from 'react';
import PropTypes from 'prop-types';
import { get, sortBy } from 'lodash';
import { gettext } from 'utils';

import PreviewBox from 'ui/components/PreviewBox';
import AgendaCoverages from './AgendaCoverages';
import {isCoverageForExtraDay, isCoverageOnPreviousDay} from '../utils';

export default function AgendaPreviewCoverages({item, planningId, group}) {
    if (get(item, 'coverages.length', 0) === 0) {
        return null;
    }

    let currentCoverage = [];
    let previousCoverage = [];
    // get current and preview coverages
    get(item, 'coverages', [])
        .forEach((coverage) => {
            if (coverage.planning_id === planningId) {
                if (isCoverageForExtraDay(coverage, group)) {
                    currentCoverage.push(coverage);
                } else if (isCoverageOnPreviousDay(coverage, group)) {
                    previousCoverage.push(coverage)
                }
            }
        });

    if (currentCoverage.length === 0 && previousCoverage.length === 0) {
        return null;
    }

    currentCoverage = sortBy(currentCoverage, 'scheduled');
    previousCoverage = sortBy(previousCoverage, 'scheduled');

    return (
        <Fragment>
            {currentCoverage.length > 0 && <PreviewBox label={gettext('Coverages')}>
                <AgendaCoverages item={item} coverages={currentCoverage}/>
            </PreviewBox>}

            {previousCoverage.length > 0 && <PreviewBox label={gettext('Previous Coverages')}>
                <AgendaCoverages item={item} coverages={previousCoverage}/>
            </PreviewBox>}
        </Fragment>
    );
}

AgendaPreviewCoverages.propTypes = {
    item: PropTypes.object,
    currentCoverage: PropTypes.arrayOf(PropTypes.object),
    previousCoverage: PropTypes.arrayOf(PropTypes.object),
};