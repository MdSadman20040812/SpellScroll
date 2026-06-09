import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const dataPath = path.join(process.cwd(), 'app', 'api', 'catalog', 'data.json');
    if (!fs.existsSync(dataPath)) {
      return NextResponse.json({ error: 'Catalog data file not found' }, { status: 404 });
    }
    
    const rawData = fs.readFileSync(dataPath, 'utf-8');
    const catalog = JSON.parse(rawData);
    
    // Strip vector embeddings to optimize bandwidth
    const sanitized = catalog.map(({ embedding, ...rest }: any) => rest);
    
    return NextResponse.json(sanitized);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
