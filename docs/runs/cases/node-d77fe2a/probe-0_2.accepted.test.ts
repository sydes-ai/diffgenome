jest.mock('winston', () => ({
  info: jest.fn(),
  debug: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
}));

import { Logger } from '../../src/lib/logger/Logger';
import * as winston from 'winston';

describe('Logger.info', () => {
  test('delegates to winston with formatted scope and args array', () => {
    const logger = new Logger('customScope');

    logger.info('hello', 42);

    expect((winston as any).info).toHaveBeenCalledTimes(1);
    expect((winston as any).info).toHaveBeenCalledWith('[customScope] hello', [42]);
  });
});
