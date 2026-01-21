import type { RequestHandler } from './$types';
import { spawn } from 'child_process';

export const GET: RequestHandler = async () => {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      // Send initial connection message
      controller.enqueue(
        encoder.encode(
          `event: log\ndata: ${JSON.stringify({ type: 'info', message: 'Starting optimization process...' })}\n\n`
        )
      );

      // Spawn the Python process using uv to access the managed venv
      const pythonProcess = spawn(
        'uv',
        ['run', 'python', 'main.py', '--data-dir', 'data', '--output-dir', 'results', '--no-viz'],
        {
          cwd: process.cwd(),
          env: {
            ...process.env,
            PYTHONUNBUFFERED: '1' // Disable Python output buffering
          }
        }
      );

      // Stream stdout
      pythonProcess.stdout.on('data', (data: Buffer) => {
        const lines = data
          .toString()
          .split('\n')
          .filter((line) => line.trim());
        for (const line of lines) {
          try {
            controller.enqueue(
              encoder.encode(`event: log\ndata: ${JSON.stringify({ type: 'stdout', message: line })}\n\n`)
            );
          } catch {
            // Controller might be closed
          }
        }
      });

      // Stream stderr
      pythonProcess.stderr.on('data', (data: Buffer) => {
        const lines = data
          .toString()
          .split('\n')
          .filter((line) => line.trim());
        for (const line of lines) {
          try {
            controller.enqueue(
              encoder.encode(`event: log\ndata: ${JSON.stringify({ type: 'stderr', message: line })}\n\n`)
            );
          } catch {
            // Controller might be closed
          }
        }
      });

      // Handle process completion
      pythonProcess.on('close', (code) => {
        try {
          if (code === 0) {
            controller.enqueue(
              encoder.encode(
                `event: complete\ndata: ${JSON.stringify({ success: true, message: 'Optimization completed successfully!' })}\n\n`
              )
            );
          } else {
            controller.enqueue(
              encoder.encode(
                `event: error\ndata: ${JSON.stringify({ success: false, message: `Process exited with code ${code}` })}\n\n`
              )
            );
          }
          controller.close();
        } catch {
          // Controller might already be closed
        }
      });

      // Handle process errors
      pythonProcess.on('error', (error) => {
        try {
          controller.enqueue(
            encoder.encode(`event: error\ndata: ${JSON.stringify({ success: false, message: error.message })}\n\n`)
          );
          controller.close();
        } catch {
          // Controller might already be closed
        }
      });
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive'
    }
  });
};
