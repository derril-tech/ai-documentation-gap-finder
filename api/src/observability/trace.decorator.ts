import { ObservabilityService } from './observability.service';

export function Trace(spanName?: string) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const observabilityService = (this as any).observabilityService as ObservabilityService;
      const finalSpanName = spanName || `${target.constructor.name}.${propertyKey}`;

      console.log(`🔍 Starting trace: ${finalSpanName}`);

      try {
        const result = await originalMethod.apply(this, args);
        console.log(`✅ Trace completed: ${finalSpanName}`);
        return result;
      } catch (error) {
        console.error(`❌ Trace failed: ${finalSpanName}`, error);

        // Capture exception if observability service is available
        if (observabilityService) {
          observabilityService.captureException(error as Error, {
            spanName: finalSpanName,
            args: args.length,
          });
        }

        throw error;
      }
    };

    return descriptor;
  };
}
