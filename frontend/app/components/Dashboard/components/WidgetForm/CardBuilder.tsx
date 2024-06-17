import React, {useEffect, useState, useCallback} from 'react';
import {observer} from 'mobx-react-lite';
import {useStore} from 'App/mstore';
import {metricOf, issueOptions, issueCategories} from 'App/constants/filterOptions';
import {FilterKey} from 'Types/filter/filterType';
import {withSiteId, dashboardMetricDetails, metricDetails} from 'App/routes';
import {Icon, confirm} from 'UI';
import {Card, Input, Space, Button} from 'antd';
import {AudioWaveform} from "lucide-react";
import FilterSeries from '../FilterSeries';
import Select from 'Shared/Select';
import MetricTypeDropdown from './components/MetricTypeDropdown';
import MetricSubtypeDropdown from './components/MetricSubtypeDropdown';
import {eventKeys} from 'App/types/filter/newFilter';
import {renderClickmapThumbnail} from './renderMap';
import FilterItem from 'Shared/Filters/FilterItem';
import {
    TIMESERIES, TABLE, CLICKMAP, FUNNEL, ERRORS, RESOURCE_MONITORING,
    PERFORMANCE, WEB_VITALS, INSIGHTS, USER_PATH, RETENTION
} from 'App/constants/card';
import {useParams} from 'react-router-dom';
import {useHistory} from "react-router";

const AIInput = ({value, setValue, placeholder, onEnter}) => (
    <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className='w-full mb-2'
        onKeyDown={(e) => e.key === 'Enter' && onEnter()}
    />
);

const PredefinedMessage = () => (
    <div className='flex items-center my-6 justify-center'>
        <Icon name='info-circle' size='18' color='gray-medium'/>
        <div className='ml-2'>Filtering and drill-downs will be supported soon for this card type.</div>
    </div>
);

const MetricOptions = ({metric, writeOption}) => {
    const isUserPath = metric.metricType === USER_PATH;

    return (
        <div className='form-group'>
            <div className='flex items-center'>
                <span className='mr-2'>Card showing</span>
                <MetricTypeDropdown onSelect={writeOption}/>
                <MetricSubtypeDropdown onSelect={writeOption}/>
                {isUserPath && (
                    <>
                        <span className='mx-3'></span>
                        <Select
                            name='startType'
                            options={[
                                {value: 'start', label: 'With Start Point'},
                                {value: 'end', label: 'With End Point'}
                            ]}
                            defaultValue={metric.startType}
                            onChange={writeOption}
                            placeholder='All Issues'
                        />
                        <span className='mx-3'>showing</span>
                        <Select
                            name='metricValue'
                            options={[
                                {value: 'location', label: 'Pages'},
                                {value: 'click', label: 'Clicks'},
                                {value: 'input', label: 'Input'},
                                {value: 'custom', label: 'Custom'},
                            ]}
                            defaultValue={metric.metricValue}
                            isMulti
                            onChange={writeOption}
                            placeholder='All Issues'
                        />
                    </>
                )}
                {metric.metricOf === FilterKey.ISSUE && metric.metricType === TABLE && (
                    <>
                        <span className='mx-3'>issue type</span>
                        <Select
                            name='metricValue'
                            options={issueOptions}
                            value={metric.metricValue}
                            onChange={writeOption}
                            isMulti
                            placeholder='All Issues'
                        />
                    </>
                )}
                {metric.metricType === INSIGHTS && (
                    <>
                        <span className='mx-3'>of</span>
                        <Select
                            name='metricValue'
                            options={issueCategories}
                            value={metric.metricValue}
                            onChange={writeOption}
                            isMulti
                            placeholder='All Categories'
                        />
                    </>
                )}
                {metric.metricType === TABLE &&
                    !(metric.metricOf === FilterKey.ERRORS || metric.metricOf === FilterKey.SESSIONS) && (
                        <>
                            <span className='mx-3'>showing</span>
                            <Select
                                name='metricFormat'
                                options={[{value: 'sessionCount', label: 'Session Count'}]}
                                defaultValue={metric.metricFormat}
                                onChange={writeOption}
                            />
                        </>
                    )}
            </div>
        </div>
    );
};

const PathAnalysisFilter = ({metric}) => (
    <div className='form-group flex flex-col'>
        {metric.startType === 'start' ? 'Start Point' : 'End Point'}
        <FilterItem
            hideDelete
            filter={metric.startPoint}
            allowedFilterKeys={[FilterKey.LOCATION, FilterKey.CLICK, FilterKey.INPUT, FilterKey.CUSTOM]}
            onUpdate={val => metric.updateStartPoint(val)}
            onRemoveFilter={() => {
            }}
        />
    </div>
);

const SeriesList = observer(() => {
    const {metricStore, dashboardStore, aiFiltersStore} = useStore();
    const metric = metricStore.instance;
    const excludeFilterKeys = [CLICKMAP, USER_PATH].includes(metric.metricType) ? eventKeys : [];
    const hasSeries = ![TABLE, FUNNEL, CLICKMAP, INSIGHTS, USER_PATH, RETENTION].includes(metric.metricType);
    const canAddSeries = metric.series.length < 3;

    return (
        <div>
            {metric.series.length > 0 && metric.series
                .slice(0, hasSeries ? metric.series.length : 1)
                .map((series, index) => (
                    <div className='mb-2' key={series.name}>
                        <FilterSeries
                            canExclude={metric.metricType === USER_PATH}
                            supportsEmpty={![CLICKMAP, USER_PATH].includes(metric.metricType)}
                            excludeFilterKeys={excludeFilterKeys}
                            observeChanges={() => metric.updateKey('hasChanged', true)}
                            hideHeader={[TABLE, CLICKMAP, INSIGHTS, USER_PATH, FUNNEL].includes(metric.metricType)}
                            seriesIndex={index}
                            series={series}
                            onRemoveSeries={() => metric.removeSeries(index)}
                            canDelete={metric.series.length > 1}
                            emptyMessage={
                                metric.metricType === TABLE
                                    ? 'Filter data using any event or attribute. Use Add Step button below to do so.'
                                    : 'Add user event or filter to define the series by clicking Add Step.'
                            }
                        />
                    </div>
                ))}
            {hasSeries && (
                <Card styles={{body: {padding: '4px'}}}>
                    <Button
                        type='link'
                        onClick={() => metric.addSeries()}
                        disabled={!canAddSeries}
                        size="small"
                    >
                        <Space>
                            <AudioWaveform size={16}/>
                            New Chart Series
                        </Space>
                    </Button>
                </Card>
            )}
        </div>
    );
});

interface RouteParams {
    siteId: string;
    dashboardId: string;
    metricId: string;
}

const CardBuilder = observer(() => {
    const history = useHistory();
    const {siteId, dashboardId} = useParams<RouteParams>();
    console.log('siteId', siteId);
    const {metricStore, dashboardStore, aiFiltersStore} = useStore();
    const [aiQuery, setAiQuery] = useState('');
    const [aiAskChart, setAiAskChart] = useState('');
    const [initialInstance, setInitialInstance] = useState(null);
    const metric = metricStore.instance;
    const timeseriesOptions = metricOf.filter(i => i.type === 'timeseries');
    const tableOptions = metricOf.filter(i => i.type === 'table');
    const isPredefined = [ERRORS, PERFORMANCE, RESOURCE_MONITORING, WEB_VITALS].includes(metric.metricType);
    const testingKey = localStorage.getItem('__mauricio_testing_access') === 'true';


    useEffect(() => {
        if (metric && !initialInstance) setInitialInstance(metric.toJson());
    }, [metric]);

    const writeOption = useCallback(({value, name}) => {
        value = Array.isArray(value) ? value : value.value;
        const obj: any = {[name]: value};
        if (name === 'metricType') {
            if (value === TIMESERIES) obj.metricOf = timeseriesOptions[0].value;
            if (value === TABLE) obj.metricOf = tableOptions[0].value;
        }
        metricStore.merge(obj);
    }, [metricStore, timeseriesOptions, tableOptions]);

    const onSave = useCallback(async () => {
        const wasCreating = !metric.exists();
        if (metric.metricType === CLICKMAP) {
            try {
                metric.thumbnail = await renderClickmapThumbnail();
            } catch (e) {
                console.error(e);
            }
        }
        const savedMetric = await metricStore.save(metric);
        setInitialInstance(metric.toJson());
        if (wasCreating) {
            const route = parseInt(dashboardId, 10) > 0
                ? withSiteId(dashboardMetricDetails(dashboardId, savedMetric.metricId), siteId)
                : withSiteId(metricDetails(savedMetric.metricId), siteId);
            history.replace(route);
            if (parseInt(dashboardId, 10) > 0) {
                dashboardStore.addWidgetToDashboard(
                    dashboardStore.getDashboard(parseInt(dashboardId, 10)),
                    [savedMetric.metricId]
                );
            }
        }
    }, [dashboardId, dashboardStore, history, metric, metricStore, siteId]);

    const onDelete = useCallback(async () => {
        if (await confirm({
            header: 'Confirm',
            confirmButton: 'Yes, delete',
            confirmation: 'Are you sure you want to permanently delete this card?'
        })) {
            metricStore.delete(metric).then(onDelete);
        }
    }, [metric, metricStore]);

    const undoChanges = useCallback(() => {
        const w = new Widget();
        metricStore.merge(w.fromJson(initialInstance), false);
    }, [initialInstance, metricStore]);

    const fetchResults = useCallback(() => aiFiltersStore.getCardFilters(aiQuery, metric.metricType)
        .then(f => metric.createSeries(f.filters)), [aiFiltersStore, aiQuery, metric]);

    const fetchChartData = useCallback(() => aiFiltersStore.getCardData(aiAskChart, metric.toJson()),
        [aiAskChart, aiFiltersStore, metric]);

    return (
        <div>
            <MetricOptions
                metric={metric}
                writeOption={writeOption}
            />
            {metric.metricType === USER_PATH && <PathAnalysisFilter metric={metric}/>}
            {isPredefined && <PredefinedMessage/>}
            {testingKey && (
                <>
                    <AIInput value={aiQuery} setValue={setAiQuery} placeholder="AI Query" onEnter={fetchResults}/>
                    <AIInput value={aiAskChart} setValue={setAiAskChart} placeholder="AI Ask Chart"
                             onEnter={fetchChartData}/>
                </>
            )}
            {aiFiltersStore.isLoading && (
                <div>
                    <div className='flex items-center font-medium py-2'>Loading</div>
                </div>
            )}
            {!isPredefined && <SeriesList/>}
        </div>
    );
});

export default CardBuilder;
