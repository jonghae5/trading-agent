import React from 'react'
import { motion } from 'framer-motion'
import { Calculator, DollarSign, PieChart } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../ui/card'

interface DiscreteAllocationProps {
  allocation: Record<string, number>
  leftoverCash: number
  weights: Record<string, number>
}

export const DiscreteAllocation: React.FC<DiscreteAllocationProps> = ({
  allocation,
  leftoverCash,
  weights
}) => {
  // 투자 금액은 $100,000 고정
  const investmentAmount = 100000
  const investedAmount = investmentAmount - leftoverCash

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const formatShares = (shares: number) => {
    return new Intl.NumberFormat('ko-KR').format(shares)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="size-5" />
          실제 매수 주식 수량 ($100,000 투자 기준)
        </CardTitle>
        <CardDescription>
          포트폴리오 가중치를 실제 매수할 수 있는 주식 수량으로 변환했습니다
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* 요약 정보 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-sm text-blue-600">총 투자 금액</div>
              <div className="text-lg font-semibold text-blue-800">
                {formatCurrency(investmentAmount)}
              </div>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-sm text-green-600">실제 투자 금액</div>
              <div className="text-lg font-semibold text-green-800">
                {formatCurrency(investedAmount)}
              </div>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <div className="text-sm text-orange-600">잔여 현금</div>
              <div className="text-lg font-semibold text-orange-800">
                {formatCurrency(leftoverCash)}
              </div>
            </div>
          </div>

          {/* 종목별 할당 */}
          <div>
            <h4 className="font-semibold mb-3 flex items-center gap-2">
              <PieChart className="size-4" />
              종목별 매수 주식 수
            </h4>
            <div className="space-y-2">
              {Object.entries(allocation).map(([ticker, shares]) => {
                const targetWeight = weights[ticker] || 0
                const actualWeight =
                  ((targetWeight * investedAmount) / investmentAmount) * 100

                return (
                  <div
                    key={ticker}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="font-medium">{ticker}</div>
                      <div className="text-sm text-gray-600">
                        {formatShares(shares)} 주 매수
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {actualWeight.toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-600">
                        {formatShares(shares)} 주
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 매수 가이드 */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h5 className="font-medium mb-2 flex items-center gap-2">
              <DollarSign className="size-4" />
              매수 가이드
            </h5>
            <div className="text-sm space-y-1">
              {Object.entries(allocation).map(([ticker, shares]) => (
                <p key={ticker}>
                  <span className="font-medium">{ticker}</span>:{' '}
                  {formatShares(shares)} 주 매수
                </p>
              ))}
              <p className="text-gray-600 mt-2">
                잔여 현금 {formatCurrency(leftoverCash)}는 현금으로 보유하거나
                추가 투자 기회를 위해 보관하세요.
              </p>
            </div>
          </div>
        </motion.div>
      </CardContent>
    </Card>
  )
}
