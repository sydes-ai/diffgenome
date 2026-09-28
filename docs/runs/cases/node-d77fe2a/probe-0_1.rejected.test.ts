import * as winston from 'winston';
import { Logger } from '../../src/lib/logger/Logger';

// Probe to ensure Logger.info executes real in-repo code and delegates to winston.info safely

test('Logger.info delegates to winston.info with formatted scope and arg array', () => {
  const originalInfo = (winston as any).info;
  const infoMock = jest.fn();
  (winston as any).info = infoMock;

  try {
    const logger = new Logger('customScope');
    logger.info('hello', 42);

    expect(infoMock).toHaveBeenCalledTimes(1);
    expect(infoMock).toHaveBeenCalledWith('[customScope] hello', [42]);
  } finally {
    // Restore to avoid leakage across tests
    (winston as any).info = originalInfo;
  }
});
