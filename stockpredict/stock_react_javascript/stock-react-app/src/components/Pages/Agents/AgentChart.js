import React from "react";
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";
import { getXAxisProps, getYAxisProps, chartColors, chartMargin } from "../../../constants/chartTheme";
import ChartWrapper from "../../ui/ChartWrapper";

import {
  elderRay,
  ema,
  sar,
  discontinuousTimeScaleProviderBuilder,
  Chart,
  ChartCanvas,
  CurrentCoordinate,
  BarSeries,
  CandlestickSeries,
  SARSeries,
  ElderRaySeries,
  LineSeries,
  MovingAverageTooltip,
  OHLCTooltip,
  SingleValueTooltip,
  lastVisibleItemBasedZoomAnchor,
  XAxis,
  YAxis,
  CrossHairCursor,
  EdgeIndicator,
  MouseCoordinateX,
  MouseCoordinateY,
  ZoomButtons,
} from "react-financial-charts";

const AgentChart = ({ initialData }) => {
  const accelerationFactor = 0.02;
  const maxAccelerationFactor = 0.2;
  const ScaleProvider = discontinuousTimeScaleProviderBuilder().inputDateAccessor(
    (d) => new Date(d.time)
  );

  const margin = chartMargin;

  // Pane heights
  const priceHeight = 450;
  const volumeHeight = 150;
  const elderRayHeight = 146;
  const height = priceHeight + volumeHeight + elderRayHeight + margin.top + margin.bottom;
  const width = 1200;

  const ema12 = ema()
    .id(1)
    .options({ windowSize: 12 })
    .merge((d, c) => { d.ema12 = c; })
    .accessor((d) => d.ema12);

  const ema26 = ema()
    .id(2)
    .options({ windowSize: 26 })
    .merge((d, c) => { d.ema26 = c; })
    .accessor((d) => d.ema26);

  const defaultSar = sar()
    .options({ accelerationFactor, maxAccelerationFactor })
    .merge((d, c) => { d.sar = c; })
    .accessor((d) => d.sar);

  const elder = elderRay();

  const calculatedData = defaultSar(elder(ema26(ema12(initialData))));
  const { data, xScale, xAccessor, displayXAccessor } = ScaleProvider(calculatedData);

  const pricesDisplayFormat = format(".2f");
  const volumeFormat = format(".2s");
  const max = xAccessor(data[data.length - 1]);
  const min = xAccessor(data[Math.max(0, data.length - 100)]);
  const xExtents = [min, max + 5];

  const dateTimeFormat = "%d %b";
  const timeDisplayFormat = timeFormat(dateTimeFormat);

  const volumeColor = (d) =>
    d.close > d.open ? chartColors.greenVolume : chartColors.redVolume;

  const openCloseColor = (d) =>
    d.close > d.open ? chartColors.greenCandle : chartColors.redCandle;

  return (
    <ChartWrapper yAxisTitle="Price (VND)" xAxisTitle="Date">
      <ChartCanvas
        height={height}
        ratio={3}
        width={width}
        margin={margin}
        data={data}
        displayXAccessor={displayXAccessor}
        seriesName="Data"
        xScale={xScale}
        xAccessor={xAccessor}
        xExtents={xExtents}
        zoomAnchor={lastVisibleItemBasedZoomAnchor}
      >
        {/* Pane 1: Price */}
        <Chart
          id={1}
          height={priceHeight}
          origin={[0, 0]}
          yExtents={(d) => [d.high, d.low]}
        >
          <XAxis {...getXAxisProps({ showTickLabel: false })} />
          <YAxis tickFormat={pricesDisplayFormat} {...getYAxisProps()} />
          <CandlestickSeries />
          <LineSeries yAccessor={ema26.accessor()} strokeStyle={ema26.stroke()} />
          <CurrentCoordinate yAccessor={ema26.accessor()} fillStyle={ema26.stroke()} />
          <LineSeries yAccessor={ema12.accessor()} strokeStyle={ema12.stroke()} />
          <CurrentCoordinate yAccessor={ema12.accessor()} fillStyle={ema12.stroke()} />
          <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
          <EdgeIndicator
            itemType="last"
            rectWidth={margin.right}
            fill={openCloseColor}
            lineStroke={openCloseColor}
            displayFormat={pricesDisplayFormat}
            yAccessor={(d) => d.close}
          />
          <SARSeries yAccessor={(d) => d.sar} />
          <MovingAverageTooltip
            origin={[8, 24]}
            options={[
              {
                yAccessor: ema26.accessor(),
                type: "EMA",
                stroke: ema26.stroke(),
                windowSize: ema26.options().windowSize,
              },
              {
                yAccessor: ema12.accessor(),
                type: "EMA",
                stroke: ema12.stroke(),
                windowSize: ema12.options().windowSize,
              },
            ]}
          />
          <ZoomButtons />
          <OHLCTooltip origin={[8, 16]} />
        </Chart>

        {/* Pane 2: Volume */}
        <Chart
          id={2}
          height={volumeHeight}
          origin={[0, priceHeight]}
          yExtents={(d) => d.volume}
        >
          <XAxis {...getXAxisProps({ showTickLabel: false })} />
          <YAxis tickFormat={volumeFormat} {...getYAxisProps()} />
          <BarSeries fillStyle={volumeColor} yAccessor={(d) => d.volume} />
          <MouseCoordinateY rectWidth={margin.right} displayFormat={volumeFormat} />
        </Chart>

        {/* Pane 3: Elder Ray */}
        <Chart
          id={3}
          height={elderRayHeight}
          origin={[0, priceHeight + volumeHeight]}
          yExtents={[0, elder.accessor()]}
          padding={{ top: 8, bottom: 8 }}
        >
          <XAxis {...getXAxisProps()} />
          <YAxis ticks={4} tickFormat={pricesDisplayFormat} {...getYAxisProps()} />
          <MouseCoordinateX displayFormat={timeDisplayFormat} />
          <MouseCoordinateY rectWidth={margin.right} displayFormat={pricesDisplayFormat} />
          <ElderRaySeries yAccessor={elder.accessor()} />
          <SingleValueTooltip
            yAccessor={elder.accessor()}
            yLabel="Elder Ray"
            yDisplayFormat={(d) =>
              `${pricesDisplayFormat(d.bullPower)}, ${pricesDisplayFormat(d.bearPower)}`
            }
            origin={[8, 16]}
          />
        </Chart>

        <CrossHairCursor />
      </ChartCanvas>
    </ChartWrapper>
  );
};

export default AgentChart;
