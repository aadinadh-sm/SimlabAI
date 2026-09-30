import React, { useState } from 'react';
import {
  GraduationCap,
  CheckCircle,
  HelpCircle,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  BookOpen
} from 'lucide-react';
import { Experiment, VivaQuestion } from '../types';

interface VivaPageProps {
  experiments: Experiment[];
}

export const VivaPage: React.FC<VivaPageProps> = ({ experiments }) => {
  const [selectedExp, setSelectedExp] = useState<number>(1);
  const [currentQIndex, setCurrentQIndex] = useState<number>(0);
  const [userAnswer, setUserAnswer] = useState<string>('');
  const [assessment, setAssessment] = useState<{
    status: 'correct' | 'partial' | 'review';
    feedback: string;
    matchedConcepts: string[];
    missedConcepts: string[];
  } | null>(null);

  const expData = experiments.find((e) => e.exp_number === selectedExp);
  const questions: VivaQuestion[] = expData?.viva_questions || [
    {
      question: "What is the main objective of this experiment?",
      expected_answer: "To simulate and verify the circuit behavior in accordance with syllabus specifications.",
      key_concepts: ["simulate", "verify", "circuit behavior"]
    }
  ];

  const currentQ = questions[currentQIndex] || questions[0];

  const handleEvaluate = () => {
    if (!userAnswer.trim()) return;

    const lowerAns = userAnswer.toLowerCase();
    const matched: string[] = [];
    const missed: string[] = [];

    currentQ.key_concepts.forEach((concept) => {
      if (lowerAns.includes(concept.toLowerCase()) || concept.split(' ').some(w => w.length > 3 && lowerAns.includes(w.toLowerCase()))) {
        matched.push(concept);
      } else {
        missed.push(concept);
      }
    });

    const ratio = matched.length / (currentQ.key_concepts.length || 1);
    let status: 'correct' | 'partial' | 'review' = 'review';
    let feedback = '';

    if (ratio >= 0.7) {
      status = 'correct';
      feedback = 'Excellent answer! You captured the essential engineering principles accurately.';
    } else if (ratio >= 0.35) {
      status = 'partial';
      feedback = 'Good attempt. You touched on the core concepts, but missed key technical details.';
    } else {
      status = 'review';
      feedback = 'Needs review. Compare your explanation with the documented model answer below.';
    }

    setAssessment({
      status,
      feedback,
      matchedConcepts: matched,
      missedConcepts: missed
    });
  };

  const handleNext = () => {
    setUserAnswer('');
    setAssessment(null);
    setCurrentQIndex((prev) => (prev + 1) % questions.length);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 select-text">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight flex items-center space-x-2">
            <GraduationCap className="w-5 h-5 text-emerald-400" />
            <span>Interactive Viva Practice</span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Test your conceptual understanding across all 14 simulation experiments with instant semantic feedback.
          </p>
        </div>

        {/* Experiment Selector */}
        <select
          value={selectedExp}
          onChange={(e) => {
            setSelectedExp(parseInt(e.target.value));
            setCurrentQIndex(0);
            setUserAnswer('');
            setAssessment(null);
          }}
          className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-700"
        >
          {experiments.map((e) => (
            <option key={e.exp_number} value={e.exp_number}>
              Exp {e.exp_number}: {e.title.slice(0, 30)}...
            </option>
          ))}
        </select>
      </div>

      {/* Question Card */}
      <div className="p-6 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-4">
        <div className="flex items-center justify-between text-xs font-mono text-zinc-500">
          <span className="text-emerald-400">
            QUESTION {currentQIndex + 1} OF {questions.length}
          </span>
          <span>Exp {selectedExp} · Standard Viva Bank</span>
        </div>

        <h2 className="text-base font-medium text-zinc-100 leading-snug">
          {currentQ.question}
        </h2>

        {/* Answer Input */}
        <div className="space-y-2 pt-2">
          <label className="text-xs font-mono text-zinc-400 block">YOUR ANSWER:</label>
          <textarea
            value={userAnswer}
            onChange={(e) => setUserAnswer(e.target.value)}
            disabled={assessment !== null}
            placeholder="Type your explanation using relevant engineering terms..."
            rows={4}
            className="w-full p-3 rounded bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-700 resize-none font-sans"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-3 pt-2">
          {!assessment ? (
            <button
              onClick={handleEvaluate}
              disabled={!userAnswer.trim()}
              className="px-4 py-2 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-black font-semibold text-xs flex items-center space-x-1.5 transition font-mono"
            >
              <span>SUBMIT FOR EVALUATION</span>
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="px-4 py-2 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs flex items-center space-x-1.5 transition font-mono border border-zinc-700"
            >
              <span>NEXT QUESTION</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={() => {
              setUserAnswer('');
              setAssessment(null);
            }}
            className="px-3 py-2 rounded bg-zinc-900 hover:bg-zinc-850 text-zinc-400 text-xs border border-zinc-800 transition font-mono"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Assessment Result */}
      {assessment && (
        <div className="p-6 rounded-lg bg-zinc-900/50 border border-zinc-800 space-y-4 animate-fadeIn">
          <div className="flex items-center space-x-2">
            {assessment.status === 'correct' && (
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            )}
            {assessment.status === 'partial' && (
              <HelpCircle className="w-4 h-4 text-amber-400" />
            )}
            {assessment.status === 'review' && (
              <AlertCircle className="w-4 h-4 text-rose-400" />
            )}
            <span
              className={`text-xs font-mono font-bold uppercase ${
                assessment.status === 'correct'
                  ? 'text-emerald-400'
                  : assessment.status === 'partial'
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {assessment.status === 'correct'
                ? 'ASSESSMENT: COMPREHENSIVE'
                : assessment.status === 'partial'
                ? 'ASSESSMENT: PARTIALLY CORRECT'
                : 'ASSESSMENT: REVIEW RECOMMENDED'}
            </span>
          </div>

          <p className="text-xs text-zinc-300">{assessment.feedback}</p>

          {/* Concepts Covered vs Missed */}
          <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-2">
            <div className="p-3 rounded bg-zinc-950/80 border border-zinc-800">
              <span className="text-emerald-400 font-semibold block mb-1">Concepts Identified:</span>
              {assessment.matchedConcepts.length > 0 ? (
                <ul className="list-disc list-inside text-zinc-300 space-y-0.5">
                  {assessment.matchedConcepts.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              ) : (
                <span className="text-zinc-600">None detected</span>
              )}
            </div>

            <div className="p-3 rounded bg-zinc-950/80 border border-zinc-800">
              <span className="text-amber-400 font-semibold block mb-1">Key Points Missed:</span>
              {assessment.missedConcepts.length > 0 ? (
                <ul className="list-disc list-inside text-zinc-300 space-y-0.5">
                  {assessment.missedConcepts.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              ) : (
                <span className="text-zinc-600">All key points covered</span>
              )}
            </div>
          </div>

          {/* Authoritative Model Answer */}
          <div className="pt-3 border-t border-zinc-800/80 space-y-1">
            <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
              AUTHORITATIVE LAB MANUAL ANSWER:
            </span>
            <p className="text-xs text-zinc-200 leading-relaxed font-sans bg-zinc-950/60 p-3 rounded border border-zinc-850">
              {currentQ.expected_answer}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
