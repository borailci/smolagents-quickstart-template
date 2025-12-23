import { getAllCodebases } from '@/lib/config';
import HomeClient from './HomeClient';

export default async function HomePage() {
  const codebases = getAllCodebases();

  return <HomeClient codebases={codebases} />;
}
