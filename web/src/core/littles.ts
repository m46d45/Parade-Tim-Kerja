/**
 * Little's Law metrics — port of parade_of_trades_analysis.littles_law_*.
 * Classic form (no yield loss): WIP = TH × CT
 */

import type { ParadeResult } from "./types";

export interface LittlesLawMetrics {
  throughput: number;
  avgPipelineWip: number;
  avgBufferWip: number;
  peakPipelineWip: number;
  peakBufferWip: number;
  cycleTimePipeline: number;
  cycleTimeBuffer: number;
  duration: number;
  totalUnits: number;
  yieldAssumed: number;
  checkPipeline: number;
  checkBuffer: number;
}

export interface LittlesLawSeries {
  pipelineWip: number[];
  bufferWip: number[];
  period: number[];
}

export function littlesLawSeries(result: ParadeResult): LittlesLawSeries {
  const n = result.config.trades.length;
  const pipelineWip = [0];
  const bufferWip = [0];
  for (const rec of result.history) {
    if (rec.cumulative && rec.cumulative.length >= n) {
      pipelineWip.push(Math.max(0, rec.cumulative[0] - rec.cumulative[n - 1]));
    } else {
      pipelineWip.push(0);
    }
    bufferWip.push(rec.buffers?.length ? rec.buffers.reduce((a, b) => a + b, 0) : 0);
  }
  return {
    pipelineWip,
    bufferWip,
    period: pipelineWip.map((_, i) => i),
  };
}

export function littlesLawMetrics(result: ParadeResult): LittlesLawMetrics {
  const total = result.config.totalUnits;
  const duration = Math.max(1, result.duration | 0);
  const th = total / duration;

  const series = littlesLawSeries(result);
  const avgPipe =
    series.pipelineWip.reduce((a, b) => a + b, 0) / series.pipelineWip.length;
  const avgBuf =
    series.bufferWip.reduce((a, b) => a + b, 0) / series.bufferWip.length;
  const peakPipe = Math.max(...series.pipelineWip);
  const peakBuf = Math.max(...series.bufferWip);

  const ctPipe = th > 0 ? avgPipe / th : Infinity;
  const ctBuf = th > 0 ? avgBuf / th : Infinity;

  return {
    throughput: th,
    avgPipelineWip: avgPipe,
    avgBufferWip: avgBuf,
    peakPipelineWip: peakPipe,
    peakBufferWip: peakBuf,
    cycleTimePipeline: ctPipe,
    cycleTimeBuffer: ctBuf,
    duration,
    totalUnits: total,
    yieldAssumed: 1,
    checkPipeline: th > 0 && Number.isFinite(ctPipe) ? th * ctPipe : 0,
    checkBuffer: th > 0 && Number.isFinite(ctBuf) ? th * ctBuf : 0,
  };
}
